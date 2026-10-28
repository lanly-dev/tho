# Thơ

Thơ — "poem" — is a small but complete programming language whose source reads
like a modern Vietnamese poem. Programs use Vietnamese words, digits,
whitespace and line breaks; there is no punctuation in the code itself.
Statements are lines of free verse, blocks close with the line `thế thôi`
("that's all"), and a program is meant to be read aloud as much as run.

Thơ follows [Wenyan-lang](https://github.com/LingDong-/wenyan-lang) in writing
real programs in a natural language, but where Wenyan imitates Classical
Chinese prose, Thơ imitates modern Vietnamese free verse: short lines,
everyday words, no metre, no rhyme.

## Quick start

A Thơ program is a `.tho` file:

```
python tho.py examples/hello.tho
```

Output:

```
chào buổi sáng
hôm nay trời rất xanh
tuổi tôi là
20
```

The other poems:

```
python tho.py examples/fizzbuzz.tho
python tho.py examples/factorial.tho
python tho.py examples/fibonacci.tho
python tho.py examples/guess.tho
```

The interpreter is a single dependency-free Python file: [tho.py](tho.py).

## A complete poem

```
ngoài lề fizzbuzz, đếm như một bài thơ
số là một
chừng nào số không lớn hơn hai mươi
  nếu số chia hết cho mười lăm
    thì thầm lời FizzBuzz
  không thì
    nếu số chia hết cho ba
      thì thầm lời Fizz
    không thì
      nếu số chia hết cho năm
        thì thầm lời Buzz
      không thì
        thì thầm số
      thế thôi
    thế thôi
  thế thôi
  từ nay số là cộng số với một
thế thôi
```

Read as Vietnamese, it says: a margin note about counting like a poem; the
number is one; as long as the number is not greater than twenty; if the number
is divisible by fifteen, whisper "FizzBuzz"; otherwise, if it is divisible by
three, whisper "Fizz"; otherwise, if it is divisible by five, whisper "Buzz";
otherwise whisper the number; that's all; from now on the number is the number
plus one; that's all.

Indentation is only for human readers. Blocks are opened by `nếu` ("if") or
`chừng nào` ("as long as") and closed by `thế thôi`; the `không thì`
("otherwise") line separates the two halves of an `nếu`.

## Language reference

### Lines and blocks

One line is one statement. A line starting with `ngoài lề` is a note to the
reader and is ignored. A line starting with `thì thầm lời` prints words and is
literal to the end of the line. Blank lines are ignored.

Indentation has no meaning. `thế thôi` closes the innermost open block, so a
poem can be laid out however it reads best.

### Names and values

A name is given a value with `là` ("is"):

```
tuổi là hai mươi
```

This creates the name or replaces an existing one. A name may contain
Vietnamese letters and digits (not as the first character), and may not be a
reserved word. Names are case-sensitive. `từ nay` ("from now on") changes only a
name that already exists, which catches typos:

```
từ nay tuổi là cộng tuổi với một
```

Values are whole numbers, unbounded in size.

### Numbers

Numbers may be written with digits or spelled in Vietnamese:

| Spelled | Value |
| --- | --- |
| `không` | 0 |
| `mười` | 10 |
| `mười lăm` | 15 |
| `hai mươi mốt` | 21 |
| `hai mươi tư` | 24 |
| `một trăm lẻ năm` | 105 |
| `một trăm linh năm` | 105 |
| `hai nghìn không trăm lẻ năm` | 2005 |
| `một triệu hai trăm nghìn` | 1,200,000 |
| `một tỷ` | 1,000,000,000 |

Digits are the fallback for anything the spelled form cannot express. Scale
words are `nghìn`, `triệu` and `tỷ`; they must strictly decrease, and two scale
words may not follow each other. That means `một nghìn tỷ` is not spelled — write
`1000000000000`. Leading zeros in digit literals are allowed and ignored.

The word `không` does double duty: as a number it is zero, and in a condition it
negates the comparison that follows.

### Expressions

Every expression is a value, a name, or an operation written with its word
first:

| Expression | Result |
| --- | --- |
| `42`, `007` | a whole number |
| `tuổi` | the value of a name |
| `cộng a với b` | `a + b` |
| `trừ a đi b` | `a − b` |
| `nhân a với b` | `a × b` |
| `chia a cho b` | `a ÷ b`, rounded towards negative infinity |
| `âm a` | `−a` |
| `ngẫu nhiên từ a đến b` | a random number from `a` to `b`, inclusive |
| `lắng nghe` | one line of input, turned into a number |

There are no parentheses. The operator word that comes first is applied last,
so `cộng nhân hai với ba với bốn` is `(2 × 3) + 4 = 10`, while
`nhân cộng hai với ba với bốn` is `(2 + 3) × 4 = 20`.

`lắng nghe` ("listen") can stand wherever a value is expected; it reads one line
from standard input, trims it, and requires a whole number. The usual form is
`tuổi là lắng nghe`.

### Conditions

A condition is always one comparison:

| Condition | True when |
| --- | --- |
| `a lớn hơn b` | `a > b` |
| `a nhỏ hơn b` | `a < b` |
| `a bằng b` | `a = b` |
| `a khác b` | `a ≠ b` |
| `a chia hết cho b` | `a` is divisible by `b` |

Put `không` immediately before the comparison to negate it:
`tuổi không lớn hơn không` means "age is not greater than zero". There is no
`và` or `hoặc`: a poem asks one question at a time, and nesting `nếu` asks the
next one.

### Statements

| Form | Meaning |
| --- | --- |
| `tên là biểu thức` | give a value a name (create or replace) |
| `từ nay tên là biểu thức` | change a name that already exists |
| `thì thầm biểu thức` | whisper a number: print it |
| `thì thầm lời ...` | whisper the literal words to the end of the line |
| `nếu ...` … `không thì` … `thế thôi` | if / otherwise |
| `chừng nào ...` … `thế thôi` | while |
| `buông` | let go: leave the innermost loop |
| `ngoài lề ...` | a note in the margin: a comment |

A text line prints exactly what follows `lời`, with surrounding spaces trimmed.
It may contain commas, question marks, quotation marks and any other
punctuation; those characters are allowed only there and in `ngoài lề` notes.
Text is not a value: it cannot be named, joined or compared.

`thì thầm lời` with nothing after it prints a blank line. Number output is
written in decimal digits, whatever form the source used.

## Why these words

The vocabulary was chosen for how it reads, not for how it maps onto English
keywords:

- `thì thầm` means "whisper", so printing is quiet. A poem is not shouted.
- `thế thôi` means "that's all". It is how a stanza ends, and it closes a block.
- `buông` means "let go". It leaves a loop, as one lets go of a thought.
- `lắng nghe` means "listen". Input is not a prompt; it is listening.
- `ngoài lề` means "in the margin". Comments are marginalia, not code.
- `từ nay` means "from now on". Changing a value is a turn in time.

## What is intentionally missing

Thơ is a small language, not a general-purpose platform:

- Values are integers only. There is no text value, so words can be printed but
  not stored, joined or compared.
- There are no user-defined functions, lists, dictionaries or modules.
- Names are global; there are no scopes.
- Conditions contain exactly one comparison, with no `và` or `hoặc`.
- There is no modulo expression; divisibility is a condition.
- `buông` leaves a loop, but there is no "continue" statement.
- There are no decimal literals and no negative literals; use `âm`.
- One statement occupies one line; an expression cannot continue onto the next.
- Punctuation is allowed in text lines and margin notes, never in code.
- Number words are reserved, so a name like `năm` ("year") or `ba` must be
  written differently.
- Error messages are in English, even though the language is Vietnamese.

These omissions keep the grammar small enough to read in one sitting, which is
the point of the experiment.

## Tests

The test suite uses only the Python standard library:

```
python -m unittest discover -s tests -v
```

It covers number words, arithmetic, naming and reassignment, conditions, loops,
`buông`, input, text lines, comments, the error paths, and every example poem.

## Files

- [tho.py](tho.py) — lexer, parser, interpreter and command-line interface
- [examples/hello.tho](examples/hello.tho) — names, numbers and whispered words
- [examples/fizzbuzz.tho](examples/fizzbuzz.tho) — conditions and divisibility
- [examples/factorial.tho](examples/factorial.tho) — an accumulating loop
- [examples/fibonacci.tho](examples/fibonacci.tho) — several names changing at once
- [examples/guess.tho](examples/guess.tho) — random numbers and listening
- [tests/test_tho.py](tests/test_tho.py) — the test suite
