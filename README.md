# Seedance TXT 分镜校验器

Python 3.9+，仅标准库，离线运行。兼容Seedance 2.0的15秒模式、Seedance 2.5的30秒模式。公开示例全部是无剧情的虚构结构占位，不含专用智能体全文或原创剧本。

## 使用

```bash
python seedance_check.py --mode 30 --final-main 1 examples/full_30.txt
python seedance_check.py --mode 30 --final-main 1 examples/final_22.txt
python seedance_check.py --mode 30 --final-main 2 examples/nonfinal_22.txt
python seedance_check.py --mode 15 --final-main 1 examples/full_15.txt
python seedance_check.py --mode 15 --final-main 1 examples/final_15_short.txt
python -m unittest discover -s tests -v
```

前三条预期依次通过、通过、失败；15秒两条通过。退出码：0通过，1校验不通过，2输入/配置/读取错误。错误报告包含文件和行号。

## 全剧末镜与批次

- 非全剧末镜必须严格等于模式标准时长。
- `--final-main N`是操作者在核对完整剧本/连续性台账后，确认全部原剧情已按序消费完毕的声明。它不是“放宽最后一个文件”的开关。仅指定编号N且N确为输入中唯一最后一镜，才允许0＜T≤标准时长。
- 不指定该参数时，没有任何短镜获得终局例外；TXT中的“全剧结束”、文件名、文件尾位置、每批第10镜均不能作为确认依据。
- 每个TXT恰为一个批次；非终局批必须10镜，已确认的终局批可为1—10镜。文件按剧情顺序显式传入，不自动按文件名排序。全局主编号连续，子编号每个主镜内从`N-01`连续递增，跨文件不重置主编号。
- 局部检查必须从批次边界开始，例如：`python seedance_check.py --mode 30 --start 11 batch02.txt`。未确认终局的局部批必须仍有10镜；只检查部分文件不能证明全剧完整。
- 多批示例：`python seedance_check.py --mode 30 --final-main 23 batch01.txt batch02.txt batch03.txt`。前两批各10镜，最后一批21—23镜。即使10或20处于文件尾，也必须30秒。
- 追加剧情后旧短末镜失去资格，必须从受影响处重排；更新终局编号不能使中途短镜继续合格。

## TXT约定

读取UTF-8（支持BOM、CRLF），标题为`【主分镜 1】（总时长：30秒）`，括号和冒号兼容半角。时长支持非负十进制小数，子镜必须大于0；用Decimal精确求和，不使用浮点误差容忍。格式请看examples；标题必须独占一行，不接受Markdown代码围栏或文件外说明。

主字段均须存在且非空：参考图、承接锚点、人物主体、单镜同框上限、人物站位、动作与表情、场景环境，以及位于所有子镜之后的末帧锚点。参考图等字段支持多行，下一已知字段前的文本归入上一字段；不适用时明确填写“无”，不能留空。

子镜以`分镜号：1-01`开头；必填时长、视角、画面描述、对白/OS、情绪节奏、音效、衔接逻辑、运镜提示。有对白/OS须非空配音指令；`对白/OS：无`时须删除配音指令整行。重复字段、错误字段归属、末帧后新增子镜均报错。标题与子镜累计必须完全一致。

本程序检查结构和数值，不能证明剧情已消费完、台词语速合法、画面连贯、音色有效或是否添加了无意义镜头；这些仍需人工/上游质量门审查。多行字段中的未知标签视作正文，不提供任意TXT格式的自动猜测转换。默认不改写输入、不联网、不输出剧本原文。请勿把真实剧本、资产库或完整智能体上传公开仓库。

30秒智能体的配套条款修改见[docs/rule_changes_30.md](docs/rule_changes_30.md)。
