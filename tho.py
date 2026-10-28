#!/usr/bin/env python3
"""Thơ: a small language whose programs read like modern Vietnamese poems.

Run a poem:
    python tho.py examples/hello.tho

Every statement is a line of free verse. Code contains no punctuation: values,
names, arithmetic and comparisons are written with Vietnamese words. A block
is closed by the line "thế thôi", the way a poem closes.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ThoError(Exception):
    """An error in a Thơ poem, optionally tied to a source line."""

    def __init__(self, message: str, line: Optional[int] = None):
        self.message = message
        self.line = line
        super().__init__(self.format())

    def format(self) -> str:
        if self.line is None:
            return self.message
        return f"line {self.line}: {self.message}"


# ---------------------------------------------------------------------------
# Tokens and lexical analysis
# ---------------------------------------------------------------------------


@dataclass
class Token:
    kind: str  # "WORD" or "NUMBER"
    text: str
    line: int


UNIT_VALUES = {
    "không": 0,
    "một": 1,
    "hai": 2,
    "ba": 3,
    "bốn": 4,
    "năm": 5,
    "sáu": 6,
    "bảy": 7,
    "tám": 8,
    "chín": 9,
}
TEN_WORD = "mười"
TENS_WORD = "mươi"
HUNDRED_WORD = "trăm"
LAST_VALUES = {word: value for word, value in UNIT_VALUES.items() if value != 0}
LAST_VALUES.update({"mốt": 1, "lăm": 5, "tư": 4})
FILLER_WORDS = {"lẻ", "linh"}
SCALE_VALUES = {"nghìn": 1_000, "triệu": 1_000_000, "tỷ": 1_000_000_000}
NUMERAL_WORDS = (
    set(UNIT_VALUES)
    | {TEN_WORD, TENS_WORD, HUNDRED_WORD}
    | set(LAST_VALUES)
    | FILLER_WORDS
    | set(SCALE_VALUES)
)
GROUP_STARTS = set(UNIT_VALUES) | {TEN_WORD}

KEYWORDS = {
    "là",
    "từ",
    "nay",
    "nếu",
    "thì",
    "chừng",
    "nào",
    "thế",
    "thôi",
    "buông",
    "thầm",
    "lời",
    "lắng",
    "nghe",
    "ngoài",
    "lề",
    "cộng",
    "với",
    "trừ",
    "đi",
    "nhân",
    "chia",
    "cho",
    "hết",
    "âm",
    "ngẫu",
    "nhiên",
    "đến",
    "lớn",
    "hơn",
    "nhỏ",
    "bằng",
    "khác",
}
RESERVED_WORDS = KEYWORDS | NUMERAL_WORDS

END_PHRASE = ("thế", "thôi")
ELSE_PHRASE = ("không", "thì")

COMMENT_PATTERN = re.compile(r"^\s*ngoài\s+lề\b")
TEXT_PATTERN = re.compile(r"^\s*thì\s+thầm\s+lời\b(?:\s*(.*))?$")


def tokenize_code(raw: str, line_number: int) -> list[Token]:
    """Split one line of code into words and numbers.

    Vietnamese letters are allowed in names, so a name may carry diacritics.
    Punctuation is refused here; it belongs in text lines or margin notes.
    """
    tokens: list[Token] = []
    index = 0
    while index < len(raw):
        character = raw[index]
        if character in " \t":
            index += 1
        elif character.isascii() and character.isdigit():
            start = index
            while index < len(raw) and raw[index].isascii() and raw[index].isdigit():
                index += 1
            tokens.append(Token("NUMBER", raw[start:index], line_number))
        elif character.isalpha():
            start = index
            index += 1
            while index < len(raw) and (
                raw[index].isalpha()
                or (raw[index].isascii() and raw[index].isdigit())
            ):
                index += 1
            tokens.append(Token("WORD", raw[start:index], line_number))
        else:
            raise ThoError(
                f"the character {character!r} is not allowed in code; "
                "put words after thì thầm lời, or explain after ngoài lề",
                line_number,
            )
    return tokens


# ---------------------------------------------------------------------------
# Abstract syntax tree
# ---------------------------------------------------------------------------


@dataclass
class Number:
    value: int


@dataclass
class Variable:
    name: str


@dataclass
class Call:
    name: str
    args: tuple


@dataclass
class Let:
    name: str
    value: object
    line: int


@dataclass
class SetVar:
    name: str
    value: object
    line: int


@dataclass
class Print:
    value: object
    line: int


@dataclass
class Say:
    text: str
    line: int


@dataclass
class Comparison:
    operator: str
    left: object
    right: object
    negated: bool


@dataclass
class If:
    condition: Comparison
    body: list
    otherwise: list
    line: int


@dataclass
class While:
    condition: Comparison
    body: list
    line: int


@dataclass
class Break:
    line: int


@dataclass
class SourceLine:
    number: int
    raw: str
    tokens: list[Token]
    text: Optional[str] = None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


COMPARATORS = (
    (("lớn", "hơn"), "greater"),
    (("nhỏ", "hơn"), "smaller"),
    (("chia", "hết", "cho"), "divisible"),
    (("bằng",), "equal"),
    (("khác",), "different"),
)


class Parser:
    def __init__(self, lines: list[SourceLine]):
        self.lines = lines

    def parse_program(self) -> list:
        statements, _ = self.parse_block(0, frozenset(), None)
        return statements

    def parse_block(self, index: int, terminators: frozenset, opener):
        """Parse lines until a terminator phrase or the end of the poem."""
        statements = []
        while index < len(self.lines):
            line = self.lines[index]
            if line.text is None and len(line.tokens) >= 2:
                phrase = (line.tokens[0].text, line.tokens[1].text)
                if phrase in terminators:
                    return statements, index
            statement, index = self.parse_statement(index)
            statements.append(statement)
        if terminators:
            opening, opening_line = opener
            raise ThoError(
                f"this {opening} is missing its thế thôi",
                opening_line,
            )
        return statements, index

    def parse_statement(self, index: int):
        line = self.lines[index]
        if line.text is not None:
            return Say(line.text, line.number), index + 1

        tokens = line.tokens
        head = tokens[0]
        word = head.text

        if head.kind != "WORD":
            raise ThoError("a line must begin with a word", line.number)

        if word == "thì":
            position = self.expect(line, 1, "thầm")
            value, position = self.parse_expression(line, position)
            self.finish_statement(line, position)
            return Print(value, line.number), index + 1

        if word == "từ":
            position = self.expect(line, 1, "nay")
            name, position = self.need_name(line, position)
            position = self.expect(line, position, "là")
            value, position = self.parse_expression(line, position)
            self.finish_statement(line, position)
            return SetVar(name.text, value, line.number), index + 1

        if word == "nếu":
            condition, position = self.parse_condition(line, 1)
            self.finish_statement(line, position)
            body, index = self.parse_block(
                index + 1, frozenset({ELSE_PHRASE, END_PHRASE}), ("nếu", line.number)
            )
            otherwise: list = []
            terminator = self.lines[index]
            if self.phrase(terminator) == ELSE_PHRASE:
                self.check_lonely(terminator, ELSE_PHRASE)
                otherwise, index = self.parse_block(
                    index + 1, frozenset({END_PHRASE}), ("nếu", line.number)
                )
                terminator = self.lines[index]
            self.check_lonely(terminator, END_PHRASE)
            return If(condition, body, otherwise, line.number), index + 1

        if word == "chừng":
            position = self.expect(line, 1, "nào")
            condition, position = self.parse_condition(line, position)
            self.finish_statement(line, position)
            body, index = self.parse_block(
                index + 1, frozenset({END_PHRASE}), ("chừng nào", line.number)
            )
            self.check_lonely(self.lines[index], END_PHRASE)
            return While(condition, body, line.number), index + 1

        if word == "buông":
            self.finish_statement(line, 1)
            return Break(line.number), index + 1

        if len(tokens) >= 2:
            phrase = (tokens[0].text, tokens[1].text)
            if phrase in (END_PHRASE, ELSE_PHRASE):
                raise ThoError(f"unexpected {' '.join(phrase)}", line.number)

        if word in RESERVED_WORDS:
            if len(tokens) >= 2 and tokens[1].text == "là":
                raise ThoError(
                    f"{word} is reserved and cannot be a name", line.number
                )
            raise ThoError(f"unexpected {word}", line.number)

        name = head
        position = self.expect(line, 1, "là")
        value, position = self.parse_expression(line, position)
        self.finish_statement(line, position)
        return Let(name.text, value, line.number), index + 1

    def parse_condition(self, line: SourceLine, position: int):
        left, position = self.parse_expression(line, position)
        negated = False
        if position < len(line.tokens) and line.tokens[position].text == "không":
            negated = True
            position += 1
        for words, operator in COMPARATORS:
            if self.matches(line, position, words):
                position += len(words)
                break
        else:
            raise ThoError(
                "expected a comparison: lớn hơn, nhỏ hơn, bằng, khác or chia hết cho",
                line.number,
            )
        right, position = self.parse_expression(line, position)
        return Comparison(operator, left, right, negated), position

    def parse_expression(self, line: SourceLine, position: int):
        tokens = line.tokens
        if position >= len(tokens):
            raise ThoError("expected a value", line.number)
        token = tokens[position]

        if token.kind == "NUMBER":
            return Number(int(token.text)), position + 1

        word = token.text
        if word in NUMERAL_WORDS:
            return self.parse_number_phrase(line, position)
        if word == "cộng":
            return self.parse_binary(line, position + 1, "với", "add")
        if word == "trừ":
            return self.parse_binary(line, position + 1, "đi", "sub")
        if word == "nhân":
            return self.parse_binary(line, position + 1, "với", "mul")
        if word == "chia":
            return self.parse_binary(line, position + 1, "cho", "div")
        if word == "âm":
            value, position = self.parse_expression(line, position + 1)
            return Call("neg", (value,)), position
        if word == "ngẫu":
            position = self.expect(line, position + 1, "nhiên")
            position = self.expect(line, position, "từ")
            low, position = self.parse_expression(line, position)
            position = self.expect(line, position, "đến")
            high, position = self.parse_expression(line, position)
            return Call("random", (low, high)), position
        if word == "lắng":
            position = self.expect(line, position + 1, "nghe")
            return Call("listen", ()), position
        if word in RESERVED_WORDS:
            raise ThoError(f"the word {word} cannot start a value", line.number)
        return Variable(word), position + 1

    def parse_binary(self, line: SourceLine, position: int, connector: str, name: str):
        left, position = self.parse_expression(line, position)
        position = self.expect(line, position, connector)
        right, position = self.parse_expression(line, position)
        return Call(name, (left, right)), position

    def parse_number_phrase(self, line: SourceLine, position: int):
        """Read a spelled Vietnamese number, scales included."""
        tokens = line.tokens
        value, position = self.parse_number_group(line, position)
        total = 0
        previous_scale = None
        while position < len(tokens) and tokens[position].text in SCALE_VALUES:
            scale_word = tokens[position].text
            if (
                position + 1 < len(tokens)
                and tokens[position + 1].text in SCALE_VALUES
            ):
                raise ThoError(
                    "two scale words cannot follow each other in a number",
                    line.number,
                )
            scale = SCALE_VALUES[scale_word]
            if previous_scale is not None and scale >= previous_scale:
                raise ThoError(
                    f"{scale_word} is out of order in this number", line.number
                )
            total += value * scale
            previous_scale = scale
            position += 1
            if position < len(tokens) and tokens[position].text in GROUP_STARTS:
                value, position = self.parse_number_group(line, position)
            else:
                value = 0
        total += value
        return Number(total), position

    def parse_number_group(self, line: SourceLine, position: int):
        """Read a group of at most three digits, 0 to 999."""
        tokens = line.tokens
        if position >= len(tokens) or tokens[position].text not in GROUP_STARTS:
            raise ThoError("expected a number", line.number)

        value = 0
        word = tokens[position].text
        if (
            word in UNIT_VALUES
            and position + 1 < len(tokens)
            and tokens[position + 1].text == HUNDRED_WORD
        ):
            value += UNIT_VALUES[word] * 100
            position += 2

        if position < len(tokens) and tokens[position].text == TEN_WORD:
            value += 10
            position += 1
            if position < len(tokens) and tokens[position].text in LAST_VALUES:
                value += LAST_VALUES[tokens[position].text]
                position += 1
        elif (
            position + 1 < len(tokens)
            and tokens[position].text in UNIT_VALUES
            and tokens[position + 1].text == TENS_WORD
        ):
            tens = UNIT_VALUES[tokens[position].text]
            if tens == 0:
                raise ThoError("không cannot stand before mươi", line.number)
            value += tens * 10
            position += 2
            if position < len(tokens) and tokens[position].text in LAST_VALUES:
                value += LAST_VALUES[tokens[position].text]
                position += 1
        elif position < len(tokens) and tokens[position].text in FILLER_WORDS:
            position += 1
            if position >= len(tokens) or tokens[position].text not in UNIT_VALUES:
                raise ThoError(
                    "lẻ and linh must be followed by a unit", line.number
                )
            value += UNIT_VALUES[tokens[position].text]
            position += 1
        elif position < len(tokens) and tokens[position].text in UNIT_VALUES:
            value += UNIT_VALUES[tokens[position].text]
            position += 1

        return value, position

    def need_name(self, line: SourceLine, position: int):
        if position >= len(line.tokens):
            raise ThoError("expected a name", line.number)
        token = line.tokens[position]
        if token.kind != "WORD":
            raise ThoError("a name must be a word", line.number)
        if token.text in RESERVED_WORDS:
            raise ThoError(
                f"{token.text} is reserved and cannot be a name", line.number
            )
        return token, position + 1

    def expect(self, line: SourceLine, position: int, word: str) -> int:
        if position >= len(line.tokens) or line.tokens[position].text != word:
            raise ThoError(f"expected {word}", line.number)
        return position + 1

    def matches(self, line: SourceLine, position: int, words: tuple) -> bool:
        if position + len(words) > len(line.tokens):
            return False
        return all(
            line.tokens[position + offset].text == word
            for offset, word in enumerate(words)
        )

    def finish_statement(self, line: SourceLine, position: int) -> None:
        if position < len(line.tokens):
            raise ThoError(
                f"unexpected {line.tokens[position].text} after this line",
                line.number,
            )

    def check_lonely(self, line: SourceLine, phrase: tuple) -> None:
        if tuple(token.text for token in line.tokens) != phrase:
            raise ThoError(
                f"{' '.join(phrase)} must be alone on its line", line.number
            )

    @staticmethod
    def phrase(line: SourceLine) -> tuple:
        return tuple(token.text for token in line.tokens[:2])


def compile_source(source: str) -> list:
    """Normalize, tokenize and parse a Thơ poem into a list of statements."""
    source = unicodedata.normalize("NFC", source)
    lines: list[SourceLine] = []
    for number, raw in enumerate(source.splitlines(), 1):
        if COMMENT_PATTERN.match(raw):
            continue
        text_match = TEXT_PATTERN.match(raw)
        if text_match:
            lines.append(
                SourceLine(number, raw, [], text=(text_match.group(1) or "").strip())
            )
            continue
        tokens = tokenize_code(raw, number)
        if not tokens:
            continue
        lines.append(SourceLine(number, raw, tokens))
    return Parser(lines).parse_program()


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


class BreakLoop(Exception):
    def __init__(self, line: int):
        self.line = line


def _read_stdin_line() -> Optional[str]:
    line = sys.stdin.readline()
    return line if line != "" else None


class Interpreter:
    def __init__(
        self,
        write: Optional[Callable[[str], None]] = None,
        read_line: Optional[Callable[[], Optional[str]]] = None,
    ):
        self.write = print if write is None else write
        self.read_line = _read_stdin_line if read_line is None else read_line
        self.variables: dict[str, int] = {}

    def execute(self, program: list) -> None:
        try:
            self.run_block(program)
        except BreakLoop as escape:
            raise ThoError(
                "buông can only be used inside a chừng nào loop", escape.line
            ) from None

    def run_block(self, statements: list) -> None:
        for statement in statements:
            self.execute_statement(statement)

    def execute_statement(self, statement) -> None:
        if isinstance(statement, Let):
            self.variables[statement.name] = self.evaluate(
                statement.value, statement.line
            )
        elif isinstance(statement, SetVar):
            if statement.name not in self.variables:
                raise ThoError(
                    f"cannot change {statement.name} because it has not been named",
                    statement.line,
                )
            self.variables[statement.name] = self.evaluate(
                statement.value, statement.line
            )
        elif isinstance(statement, Print):
            self.write(str(self.evaluate(statement.value, statement.line)))
        elif isinstance(statement, Say):
            self.write(statement.text)
        elif isinstance(statement, If):
            if self.evaluate_condition(statement.condition, statement.line):
                self.run_block(statement.body)
            else:
                self.run_block(statement.otherwise)
        elif isinstance(statement, While):
            while self.evaluate_condition(statement.condition, statement.line):
                try:
                    self.run_block(statement.body)
                except BreakLoop:
                    break
        elif isinstance(statement, Break):
            raise BreakLoop(statement.line)
        else:  # pragma: no cover - guards against future AST additions
            raise AssertionError(f"unknown statement type {type(statement).__name__}")

    def evaluate_condition(self, condition: Comparison, line: int) -> bool:
        left = self.evaluate(condition.left, line)
        right = self.evaluate(condition.right, line)
        if condition.operator == "greater":
            result = left > right
        elif condition.operator == "smaller":
            result = left < right
        elif condition.operator == "equal":
            result = left == right
        elif condition.operator == "different":
            result = left != right
        elif condition.operator == "divisible":
            if right == 0:
                raise ThoError("cannot divide by zero", line)
            result = left % right == 0
        else:  # pragma: no cover
            raise AssertionError(f"unknown comparison {condition.operator}")
        return not result if condition.negated else result

    def evaluate(self, expression, line: int) -> int:
        if isinstance(expression, Number):
            return expression.value
        if isinstance(expression, Variable):
            if expression.name not in self.variables:
                raise ThoError(
                    f"the name {expression.name} has not been given a value", line
                )
            return self.variables[expression.name]

        arguments = [self.evaluate(argument, line) for argument in expression.args]
        name = expression.name

        if name == "listen":
            return self.read_number(line)
        if name == "neg":
            return -arguments[0]
        if name == "random":
            low, high = arguments
            if low > high:
                raise ThoError(
                    "ngẫu nhiên needs a lower number that is not larger than the upper one",
                    line,
                )
            return random.randint(low, high)

        left, right = arguments
        if name == "add":
            return left + right
        if name == "sub":
            return left - right
        if name == "mul":
            return left * right
        if name == "div":
            if right == 0:
                raise ThoError("cannot divide by zero", line)
            return left // right

        raise AssertionError(f"unknown operation {name}")  # pragma: no cover

    def read_number(self, line: int) -> int:
        raw = self.read_line()
        if raw is None:
            raise ThoError("listening ended before a number was heard", line)
        text = raw.strip()
        try:
            return int(text)
        except ValueError:
            raise ThoError(
                f"listening heard {text!r}, which is not a whole number", line
            ) from None


# ---------------------------------------------------------------------------
# Command line interface
# ---------------------------------------------------------------------------


def run_file(path: str) -> int:
    try:
        source = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        print(f"thơ: cannot read {path}: {error}", file=sys.stderr)
        return 2
    try:
        program = compile_source(source)
        Interpreter().execute(program)
    except ThoError as error:
        print(f"thơ: {error.format()}", file=sys.stderr)
        return 1
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    # Vietnamese is the whole point of this language; do not let a Windows
    # console or a redirected pipe fall back to a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="thơ",
        description="Run a poem written in Thơ, a language of Vietnamese free verse.",
    )
    parser.add_argument("file", help="path to a .tho poem")
    arguments = parser.parse_args(argv)
    return run_file(arguments.file)


if __name__ == "__main__":
    sys.exit(main())
