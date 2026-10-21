import subprocess
import sys
import unittest
from pathlib import Path
from seedance_check import validate


def shot(n=1, durations=('10', '20')):
    total = sum(__import__('decimal').Decimal(x) for x in durations)
    text = f'【主分镜 {n}】（总时长：{total}秒）\n'
    for key in ('参考图', '承接锚点', '人物主体', '单镜同框上限', '人物站位', '动作与表情', '场景环境'):
        text += key + '：虚构结构测试\n'
    for i, duration in enumerate(durations, 1):
        text += f'分镜号：{n}-{i:02d}\n时长：{duration}秒\n'
        for key in ('视角', '画面描述', '对白/OS', '情绪节奏', '音效', '衔接逻辑', '运镜提示'):
            text += key + '：' + ('无' if key == '对白/OS' else '虚构结构测试') + '\n'
    return text + '末帧锚点：虚构结构测试\n'


class ValidatorTests(unittest.TestCase):
    def check(self, text, mode=30, final=1):
        return validate([('test.txt', text)], mode, final)

    def test_full_30(self):
        self.assertEqual(self.check(shot()), [])

    def test_final_22(self):
        self.assertEqual(self.check(shot(durations=('10', '12'))), [])

    def test_nonfinal_22(self):
        self.assertTrue(self.check(shot(durations=('22',)) + shot(2), final=2))

    def test_unknown_endpoint(self):
        self.assertTrue(self.check(shot(durations=('22',)), final=None))

    def test_15(self):
        self.assertEqual(self.check(shot(durations=('7', '8')), 15), [])
        self.assertEqual(self.check(shot(durations=('6.8',)), 15), [])
        self.assertTrue(self.check(shot(durations=('16',)), 15))

    def test_decimal_exact(self):
        self.assertEqual(self.check(shot(durations=('0.1', '0.2')), final=1), [])

    def test_sum(self):
        self.assertTrue(self.check(shot().replace('总时长：30', '总时长：29')))

    def test_numbering(self):
        for old, new in [('主分镜 1', '主分镜 2'), ('1-02', '1-03'), ('1-01', '2-01')]:
            with self.subTest(old=old):
                self.assertTrue(self.check(shot().replace(old, new)))

    def test_fields(self):
        self.assertTrue(self.check(shot().replace('视角：虚构结构测试', '视角：')))
        self.assertTrue(self.check(shot().replace('场景环境：虚构结构测试\n', '')))

    def test_voice(self):
        text = shot().replace('对白/OS：无', '对白/OS：测试：“开始。”')
        self.assertTrue(self.check(text))
        self.assertEqual(self.check(text.replace('情绪节奏：', '配音指令：测试声音\n情绪节奏：')), [])
        self.assertTrue(self.check(shot().replace('情绪节奏：', '配音指令：\n情绪节奏：')))

    def test_batches(self):
        batch = ''.join(shot(i) for i in range(1, 11))
        self.assertEqual(validate([('a', batch), ('b', shot(11, ('22',)))], 30, 11), [])
        self.assertTrue(validate([('a', batch.replace('总时长：30', '总时长：22')), ('b', shot(11))], 30, 11))
        self.assertTrue(validate([('a', shot()), ('b', shot(2))], 30, 2))
        self.assertTrue(validate([('a', batch + shot(11))], 30, 11))
        self.assertTrue(validate([('a', batch), ('b', shot())], 30, 1))
        self.assertEqual(validate([('a', batch)], 30), [])
        self.assertEqual(validate([('b', shot(11, ('22',)))], 30, 11, 11), [])

    def test_bad_input(self):
        for text in ('', '【主分镜 X】（总时长：T秒）', shot(durations=('0',)), shot(durations=('31',))):
            self.assertTrue(self.check(text))
        self.assertTrue(self.check(shot().replace('时长：10秒', '时长：NaN秒')))
        self.assertTrue(self.check(shot().replace('时长：10秒', '时长：-10秒')))

    def test_order_and_duplicates(self):
        self.assertTrue(self.check(shot().replace('视角：', '时长：10秒\n视角：')))
        self.assertTrue(self.check(shot() + '分镜号：1-03\n时长：1秒'))

    def test_cli(self):
        root = Path(__file__).resolve().parents[1]
        for file, final, code in [('full_30.txt', '1', 0), ('final_22.txt', '1', 0), ('nonfinal_22.txt', '2', 1), ('full_15.txt', '1', 0)]:
            result = subprocess.run([sys.executable, str(root / 'seedance_check.py'), '--mode', '15' if '15' in file else '30', '--final-main', final, str(root / 'examples' / file)], capture_output=True)
            self.assertEqual(result.returncode, code, result.stdout)


if __name__ == '__main__':
    unittest.main()
