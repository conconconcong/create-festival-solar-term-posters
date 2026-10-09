# Sunny & Molly 节日节气海报 Skill

为众安宠物险 Sunny（小帅）与 Molly（茉莉）制作节日、节气和营销节点竖版海报。

本仓库发布的是**独立标题流程版本**：一次生成无字主视觉，再生成原创中文标题素材，最后用 Python 合成标题、固定文案、真实 Logo 和二维码。

## 仓库内容

- [`create-festival-solar-term-posters`](skills/create-festival-solar-term-posters/SKILL.md)：主海报技能，包含角色母版、品牌素材、文案字体、参考规范和合成脚本。
- [`festival-poster-title-typography`](skills/festival-poster-title-typography/SKILL.md)：配套中文标题技能，生成独立原创标题素材。

两项技能需要一起安装。生图依赖运行环境提供的图像生成工具；Python 脚本只负责后期合成，不会自行调用生图 API。

## 安装

下载或克隆本仓库：

```bash
git clone https://github.com/conconconcong/create-festival-solar-term-posters.git
```

将 `skills/` 下的两个完整文件夹放入 Codex 的技能目录（通常为 `~/.codex/skills/`；自定义配置时使用相应技能目录）。已有同名技能时，先备份旧目录再替换。

合成脚本需要 Python 3.10 或更新版本以及 Pillow：

```bash
python3 -m pip install -r requirements.txt
```

## 使用

在支持上述技能和图像生成的 Codex 环境中输入：

```text
用 $create-festival-solar-term-posters 做一张霜降海报。
```

也可以提供场景、动作、标题或文案。默认成片尺寸为 **1080 × 2333 px**。

## 海报案例

以下为用户提供的秋分与七夕海报案例，保留原图（1080 × 2335 px）；点击图片可查看完整尺寸。

| 秋分 | 七夕 |
| :---: | :---: |
| [![秋分海报：小帅与茉莉在金色秋叶间望向飞鸟](examples/autumn-equinox.jpg)](examples/autumn-equinox.jpg) | [![七夕海报：小帅与茉莉相依乘鹊，穿行星空](examples/qixi.jpg)](examples/qixi.jpg) |

## 制作流程

1. 选择一个节点符号和一个业务模式：风险发现、准备清单、保障科普、应急路径或长期陪伴。
2. 依据角色母版生成无字主视觉，预留标题和品牌区域。
3. 依据实际主视觉设计、生成并校对独立标题。
4. 合成标题、阿里妈妈方圆体 Bold 文案、真实 Logo 和二维码。
5. 检查完整尺寸和缩略图后交付。

合成命令示例（在主技能目录运行）：

```bash
python3 scripts/compose_poster.py \
  --input main-visual.png \
  --title-art title.png \
  --title-box 160,260,760,280 \
  --copy "寒意早察觉\n温暖早准备" \
  --logo auto --qr auto \
  --output poster.png
```

标题文件应为真正透明 PNG；单色键底素材需使用 `--title-bg '#RRGGBB'` 指定底色。最终仍需检查字形、透明边缘、角色结构和二维码静区。

## 素材说明

本仓库包含角色母版、品牌标识、投保二维码和字体文件，用于复现技能工作流。公开仓库不表示授予这些素材的商标、角色或字体再授权；相关权利及适用许可仍归各自权利人。仓库未另行指定开源许可证。
