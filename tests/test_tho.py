import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tho import Interpreter, ThoError, compile_source  # noqa: E402


def run(source, inputs=()):
    pending = list(inputs)

    def read_line():
        return pending.pop(0) if pending else None

    output = []
    program = compile_source(source)
    Interpreter(write=output.append, read_line=read_line).execute(program)
    return output


class NumberTests(unittest.TestCase):
    def spoken(self, phrase):
        return run(f"x là {phrase}\nthì thầm x")

    def test_digits(self):
        self.assertEqual(run("x là 42\nthì thầm x"), ["42"])

    def test_leading_zeros(self):
        self.assertEqual(run("x là 007\nthì thầm x"), ["7"])

    def test_simple_number_words(self):
        self.assertEqual(self.spoken("ba"), ["3"])
        self.assertEqual(self.spoken("mười"), ["10"])
        self.assertEqual(self.spoken("không"), ["0"])

    def test_compound_number_words(self):
        self.assertEqual(self.spoken("mười lăm"), ["15"])
        self.assertEqual(self.spoken("hai mươi mốt"), ["21"])
        self.assertEqual(self.spoken("hai mươi tư"), ["24"])
        self.assertEqual(self.spoken("một trăm lẻ năm"), ["105"])
        self.assertEqual(self.spoken("một trăm mười lăm"), ["115"])
        self.assertEqual(self.spoken("chín trăm chín mươi chín"), ["999"])

    def test_scales(self):
        self.assertEqual(self.spoken("một nghìn"), ["1000"])
        self.assertEqual(self.spoken("hai nghìn không trăm lẻ năm"), ["2005"])
        self.assertEqual(self.spoken("một triệu hai trăm nghìn"), ["1200000"])
        self.assertEqual(self.spoken("một tỷ"), ["1000000000"])

    def test_bad_number_words(self):
        with self.assertRaises(ThoError) as context:
            run("x là trăm")
        self.assertIn("expected a number", str(context.exception))

    def test_filler_needs_a_unit(self):
        with self.assertRaises(ThoError) as context:
            run("x là lẻ năm")
        self.assertIn("expected a number", str(context.exception))
        with self.assertRaises(ThoError) as context:
            run("x là một trăm lẻ")
        self.assertIn("followed by a unit", str(context.exception))

    def test_scales_must_get_smaller(self):
        with self.assertRaises(ThoError) as context:
            run("x là một triệu nghìn")
        self.assertIn("scale words", str(context.exception))

    def test_number_words_must_not_run_together(self):
        with self.assertRaises(ThoError) as context:
            run("x là một hai")
        self.assertIn("unexpected hai", str(context.exception))


class ExpressionTests(unittest.TestCase):
    def evaluate(self, expression):
        return run(f"x là {expression}\nthì thầm x")

    def test_arithmetic(self):
        self.assertEqual(self.evaluate("cộng hai với ba"), ["5"])
        self.assertEqual(self.evaluate("trừ mười đi bốn"), ["6"])
        self.assertEqual(self.evaluate("nhân bốn với năm"), ["20"])
        self.assertEqual(self.evaluate("chia bảy cho hai"), ["3"])
        self.assertEqual(self.evaluate("âm năm"), ["-5"])

    def test_nested_arithmetic_needs_no_parentheses(self):
        self.assertEqual(self.evaluate("cộng nhân hai với ba với bốn"), ["10"])
        self.assertEqual(self.evaluate("nhân cộng hai với ba với bốn"), ["20"])

    def test_division_by_zero(self):
        with self.assertRaises(ThoError) as context:
            self.evaluate("chia một cho không")
        self.assertIn("divide by zero", str(context.exception))

    def test_random_is_inclusive(self):
        with mock.patch("tho.random.randint", return_value=7) as randint:
            self.assertEqual(self.evaluate("ngẫu nhiên từ một đến mười"), ["7"])
        randint.assert_called_once_with(1, 10)

    def test_random_needs_a_sensible_range(self):
        with self.assertRaises(ThoError) as context:
            self.evaluate("ngẫu nhiên từ mười đến một")
        self.assertIn("lower number", str(context.exception))

    def test_listening(self):
        output = run("x là lắng nghe\nthì thầm x", ["21"])
        self.assertEqual(output, ["21"])

    def test_listening_at_the_end(self):
        with self.assertRaises(ThoError) as context:
            run("x là lắng nghe")
        self.assertIn("listening ended", str(context.exception))

    def test_listening_to_nonsense(self):
        with self.assertRaises(ThoError) as context:
            run("x là lắng nghe", ["hello"])
        self.assertIn("not a whole number", str(context.exception))


class VariableTests(unittest.TestCase):
    def test_naming_and_changing(self):
        source = "\n".join(
            ["tuổi là hai mươi", "từ nay tuổi là cộng tuổi với một", "thì thầm tuổi"]
        )
        self.assertEqual(run(source), ["21"])

    def test_a_name_can_be_given_again(self):
        source = "\n".join(["x là một", "x là hai", "thì thầm x"])
        self.assertEqual(run(source), ["2"])

    def test_changing_an_unnamed_value(self):
        with self.assertRaises(ThoError) as context:
            run("từ nay x là 1")
        self.assertIn("has not been named", str(context.exception))
        self.assertEqual(context.exception.line, 1)

    def test_unknown_name(self):
        with self.assertRaises(ThoError) as context:
            run("ngoài lề bắt đầu\nthì thầm thiếu")
        self.assertIn("has not been given a value", str(context.exception))
        self.assertEqual(context.exception.line, 2)

    def test_reserved_word_as_name(self):
        with self.assertRaises(ThoError) as context:
            run("ba là 5")
        self.assertIn("reserved", str(context.exception))

    def test_names_carry_diacritics(self):
        self.assertEqual(run("tuổi là ba\nthì thầm tuổi"), ["3"])

    def test_value_must_be_given(self):
        with self.assertRaises(ThoError) as context:
            run("tuổi là")
        self.assertIn("expected a value", str(context.exception))


class ControlFlowTests(unittest.TestCase):
    def test_if_true(self):
        self.assertEqual(
            run("nếu một nhỏ hơn hai\nthì thầm lời đúng\nthế thôi"), ["đúng"]
        )

    def test_if_false_without_else(self):
        self.assertEqual(
            run("nếu một lớn hơn hai\nthì thầm lời sai\nthế thôi"), []
        )

    def test_if_false_with_else(self):
        source = "\n".join(
            [
                "nếu một lớn hơn hai",
                "  thì thầm lời sai",
                "không thì",
                "  thì thầm lời đúng",
                "thế thôi",
            ]
        )
        self.assertEqual(run(source), ["đúng"])

    def test_nested_if(self):
        source = "\n".join(
            [
                "x là năm",
                "nếu x lớn hơn không",
                "  nếu x lớn hơn mười",
                "    thì thầm lời lớn",
                "  không thì",
                "    thì thầm lời nhỏ",
                "  thế thôi",
                "thế thôi",
            ]
        )
        self.assertEqual(run(source), ["nhỏ"])

    def test_while_loop(self):
        source = "\n".join(
            [
                "tổng là không",
                "n là một",
                "chừng nào n không lớn hơn năm",
                "  từ nay tổng là cộng tổng với n",
                "  từ nay n là cộng n với một",
                "thế thôi",
                "thì thầm tổng",
            ]
        )
        self.assertEqual(run(source), ["15"])

    def test_buong_leaves_the_loop(self):
        source = "\n".join(
            [
                "n là không",
                "chừng nào n nhỏ hơn mười",
                "  nếu n bằng ba",
                "    buông",
                "  thế thôi",
                "  thì thầm n",
                "  từ nay n là cộng n với một",
                "thế thôi",
                "thì thầm lời xong",
            ]
        )
        self.assertEqual(run(source), ["0", "1", "2", "xong"])

    def test_buong_outside_a_loop(self):
        with self.assertRaises(ThoError) as context:
            run("buông")
        self.assertIn("inside a chừng nào loop", str(context.exception))

    def test_missing_closing_line(self):
        with self.assertRaises(ThoError) as context:
            compile_source("nếu một nhỏ hơn hai\nthì thầm lời đúng\n")
        self.assertIn("missing its thế thôi", str(context.exception))

    def test_stray_closing_line(self):
        with self.assertRaises(ThoError) as context:
            compile_source("thế thôi")
        self.assertIn("unexpected thế thôi", str(context.exception))

    def test_closing_line_must_be_alone(self):
        with self.assertRaises(ThoError) as context:
            compile_source("nếu một nhỏ hơn hai\nthì thầm lời đúng\nthế thôi ngay\n")
        self.assertIn("alone", str(context.exception))

    def test_khong_thi_must_be_alone(self):
        with self.assertRaises(ThoError) as context:
            compile_source(
                "nếu một nhỏ hơn hai\nthì thầm lời đúng\nkhông thì sai\nthế thôi\n"
            )
        self.assertIn("alone", str(context.exception))

    def test_khong_thi_without_an_if(self):
        with self.assertRaises(ThoError) as context:
            compile_source("không thì\n")
        self.assertIn("unexpected không thì", str(context.exception))


class TextTests(unittest.TestCase):
    def test_text_may_hold_punctuation(self):
        self.assertEqual(
            run("thì thầm lời hôm nay, trời đẹp quá!"), ["hôm nay, trời đẹp quá!"]
        )

    def test_empty_text_prints_a_blank_line(self):
        self.assertEqual(run("thì thầm lời"), [""])

    def test_internal_spacing_is_kept(self):
        self.assertEqual(run("thì thầm lời   hai  dấu cách"), ["hai  dấu cách"])

    def test_comment_can_hold_punctuation(self):
        self.assertEqual(run("ngoài lề đừng chạy dòng này!\nx là 1\nthì thầm x"), ["1"])

    def test_comment_may_touch_punctuation(self):
        self.assertEqual(run("ngoài lề, ghi chú\nthì thầm 1"), ["1"])

    def test_text_may_begin_with_punctuation(self):
        self.assertEqual(run("thì thầm lời, trời đẹp"), [", trời đẹp"])

    def test_comment_alone_is_silent(self):
        self.assertEqual(run("ngoài lề chỉ là ghi chú"), [])

    def test_blank_lines_are_ignored(self):
        self.assertEqual(run("\n\nthì thầm 1\n\n"), ["1"])

    def test_punctuation_is_not_allowed_in_code(self):
        with self.assertRaises(ThoError) as context:
            compile_source("x là 1 + 2")
        self.assertIn("not allowed", str(context.exception))
        self.assertEqual(context.exception.line, 1)


class ErrorTests(unittest.TestCase):
    def test_line_must_begin_with_a_word(self):
        with self.assertRaises(ThoError) as context:
            compile_source("5 là x")
        self.assertIn("begin with a word", str(context.exception))

    def test_malformed_line(self):
        with self.assertRaises(ThoError) as context:
            run("nhảy 5")
        self.assertIn("expected là", str(context.exception))

    def test_missing_printed_value(self):
        with self.assertRaises(ThoError) as context:
            run("thì thầm")
        self.assertIn("expected a value", str(context.exception))

    def test_extra_word_after_a_line(self):
        with self.assertRaises(ThoError) as context:
            run("thì thầm 1 2")
        self.assertIn("unexpected 2", str(context.exception))

    def test_condition_needs_a_comparison(self):
        with self.assertRaises(ThoError) as context:
            run("nếu một\nthì thầm 1\nthế thôi")
        self.assertIn("expected a comparison", str(context.exception))

    def test_condition_needs_a_right_side(self):
        with self.assertRaises(ThoError) as context:
            run("nếu một bằng\nthì thầm 1\nthế thôi")
        self.assertIn("expected a value", str(context.exception))

    def test_khong_before_a_comparison_negates_it(self):
        source = "\n".join(
            ["nếu một không bằng hai", "thì thầm lời khác", "thế thôi"]
        )
        self.assertEqual(run(source), ["khác"])


class ExampleTests(unittest.TestCase):
    def example(self, name, inputs=()):
        source = (ROOT / "examples" / name).read_text(encoding="utf-8")
        return run(source, inputs)

    def test_all_examples_compile(self):
        for path in (ROOT / "examples").glob("*.tho"):
            with self.subTest(path=path.name):
                compile_source(path.read_text(encoding="utf-8"))

    def test_hello(self):
        self.assertEqual(
            self.example("hello.tho"),
            ["chào buổi sáng", "hôm nay trời rất xanh", "tuổi tôi là", "20"],
        )

    def test_factorial(self):
        self.assertEqual(
            self.example("factorial.tho"), ["giai thừa của năm là", "120"]
        )

    def test_fibonacci(self):
        self.assertEqual(
            self.example("fibonacci.tho"),
            ["0", "1", "1", "2", "3", "5", "8", "13", "21", "34"],
        )

    def test_fizzbuzz(self):
        self.assertEqual(
            self.example("fizzbuzz.tho"),
            [
                "1",
                "2",
                "Fizz",
                "4",
                "Buzz",
                "Fizz",
                "7",
                "8",
                "Fizz",
                "Buzz",
                "11",
                "Fizz",
                "13",
                "14",
                "FizzBuzz",
                "16",
                "17",
                "Fizz",
                "19",
                "Buzz",
            ],
        )

    def test_guess_game(self):
        with mock.patch("tho.random.randint", return_value=42):
            output = self.example("guess.tho", ["50", "75", "42"])
        self.assertEqual(
            output,
            [
                "tôi đang nghĩ một con số từ một đến một trăm",
                "con số của tôi nhỏ hơn thế",
                "con số của tôi nhỏ hơn thế",
                "đúng rồi",
            ],
        )


if __name__ == "__main__":
    unittest.main()
