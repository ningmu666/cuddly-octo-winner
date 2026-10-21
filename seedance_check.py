#!/usr/bin/env python3
"""Validate Seedance TXT structure without reading or transmitting story assets."""
import argparse
from decimal import Decimal
from pathlib import Path
import re
import sys

NUMBER = r'(?:0|[1-9]\d*)(?:\.\d+)?'
TITLE = re.compile(r'【主分镜\s*(\d+)】\s*[（(]总时长\s*[：:]\s*(' + NUMBER + r')秒[）)]')
FIELD = re.compile(r'^([^：:]+)[：:]\s*(.*)$')
MAIN = ('参考图', '承接锚点', '人物主体', '单镜同框上限', '人物站位', '动作与表情', '场景环境')
SUB = ('时长', '视角', '画面描述', '对白/OS', '情绪节奏', '音效', '衔接逻辑', '运镜提示')
KNOWN = set(MAIN + SUB + ('分镜号', '配音指令', '末帧锚点'))


def validate(batches, mode=30, final_main=None, start=1):
    """batches: ordered (filename, text) pairs; each file is one batch.

    final_main is an operator-confirmed story endpoint, never inferred from TXT.
    start permits an explicit partial run beginning at a global batch boundary.
    Returns location-prefixed errors. Decimal provides exact decimal sums.
    """
    if mode not in (15, 30) or start < 1 or (start - 1) % 10:
        raise ValueError('mode必须15/30；start必须为1、11、21……')
    errors = []
    expected = start
    seen = []
    def fail(where, message):
        errors.append(f'{where}: {message}')
    for filename, text in batches:
        where = str(filename)
        blocks = []
        current = None
        for line_no, raw in enumerate(text.lstrip('\ufeff').splitlines(), 1):
            line = raw.strip()
            loc = f'{filename}:{line_no}'
            if not line:
                continue
            match = TITLE.fullmatch(line)
            if match:
                current = {'id': int(match[1]), 'duration': Decimal(match[2]),
                           'fields': {}, 'subs': [], 'loc': loc, 'end': False}
                blocks.append(current)
                target = current['fields']
                last_key = None
                continue
            if '【主分镜' in line:
                fail(loc, '主分镜标题格式错误')
                current = None
                continue
            if current is None:
                fail(loc, '主分镜外存在无法识别的内容')
                continue
            match = FIELD.fullmatch(line)
            if match and match[1].strip() in KNOWN:
                key, value = match[1].strip(), match[2].strip()
                if key == '分镜号':
                    if current['end']:
                        fail(loc, '末帧锚点之后不能再有子分镜')
                    sub = {'number': value, 'fields': {}, 'loc': loc}
                    current['subs'].append(sub)
                    target = sub['fields']
                    last_key = None
                    continue
                if key == '末帧锚点':
                    if not current['subs']:
                        fail(loc, '末帧锚点必须在所有子分镜之后')
                    current['end'] = True
                    target = current['fields']
                elif current['end']:
                    fail(loc, '末帧锚点之后存在额外字段')
                elif key in MAIN and current['subs']:
                    fail(loc, '主分镜字段必须位于子分镜之前')
                elif key in SUB + ('配音指令',) and not current['subs']:
                    fail(loc, '子分镜字段缺少分镜号')
                if key in target:
                    fail(loc, f'字段重复：{key}')
                target[key] = value
                last_key = key
            elif last_key:
                target[last_key] += '\n' + line
            else:
                fail(loc, '无所属字段的文本')
        if not blocks:
            fail(where, '没有主分镜')
        if len(blocks) > 10:
            fail(where, '单批不得超过10个主分镜')
        is_final_batch = bool(blocks and final_main == blocks[-1]['id'])
        if len(blocks) != 10 and not is_final_batch:
            fail(where, '不足10镜的批次必须有明确的全剧末镜确认')
        for block in blocks:
            loc = block['loc']
            ident, duration = block['id'], block['duration']
            seen.append(ident)
            if ident != expected:
                fail(loc, f'主分镜编号应为{expected}，实际为{ident}')
            expected += 1
            if final_main == ident:
                if not Decimal(0) < duration <= Decimal(mode):
                    fail(loc, f'全剧末镜必须满足0＜T≤{mode}')
            elif duration != Decimal(mode):
                fail(loc, f'非已确认全剧末镜必须为{mode}秒（不能把文件尾当剧终）')
            for key in MAIN + ('末帧锚点',):
                if not block['fields'].get(key, '').strip():
                    fail(loc, f'缺少或为空：{key}')
            total = Decimal(0)
            if not block['subs']:
                fail(loc, '缺少子分镜')
            for index, sub in enumerate(block['subs'], 1):
                fields, sloc = sub['fields'], sub['loc']
                if sub['number'] != f'{ident}-{index:02d}':
                    fail(sloc, f'子分镜编号应为{ident}-{index:02d}')
                for key in SUB:
                    if not fields.get(key, '').strip():
                        fail(sloc, f'缺少或为空：{key}')
                value = fields.get('时长', '')
                if not re.fullmatch(NUMBER + '秒', value):
                    fail(sloc, '时长必须为非负十进制数字加秒')
                else:
                    seconds = Decimal(value[:-1])
                    if seconds <= 0:
                        fail(sloc, '子分镜时长必须大于0')
                    total += seconds
                dialogue = fields.get('对白/OS', '').strip()
                if dialogue and dialogue != '无' and not fields.get('配音指令', '').strip():
                    fail(sloc, '有对白/OS必须填写配音指令')
                if dialogue == '无' and '配音指令' in fields:
                    fail(sloc, '无对白/OS应删除配音指令整行')
            if total != duration:
                fail(loc, f'子分镜累计{total}秒，不等于标题{duration}秒')
    if not seen:
        fail('输入', '没有可校验的主分镜')
    if final_main is not None and (not seen or final_main != seen[-1] or seen.count(final_main) != 1):
        fail('输入', '已确认的全剧末镜必须唯一且位于所有输入的最后')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path, help='按剧情顺序输入，每个TXT为一个批次')
    parser.add_argument('--mode', type=int, choices=(15, 30), required=True)
    parser.add_argument('--final-main', type=int, help='人工核对全剧内容已消费完后填写末镜全局编号')
    parser.add_argument('--start', type=int, default=1, help='局部批次的全局起号，必须1/11/21……')
    args = parser.parse_args(argv)
    try:
        paths = [p.resolve() for p in args.files]
        if len(set(paths)) != len(paths):
            parser.error('输入文件重复')
        batches = [(str(p), p.read_text(encoding='utf-8-sig')) for p in args.files]
        errors = validate(batches, args.mode, args.final_main, args.start)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f'输入错误：{exc}', file=sys.stderr)
        return 2
    for error in errors:
        print(error)
    print(f'校验失败：{len(errors)}项' if errors else '校验通过（结构与时长；剧情终局资格由操作者确认）')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
