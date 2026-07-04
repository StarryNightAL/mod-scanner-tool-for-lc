# Mod Scanner Tool for Lobotomy Corporation

扫描《脑叶公司》(Lobotomy Corporation) Mod 文件并整理信息的工具集。

## 功能

- 递归搜索 Mod 文件夹中的 Equipment ID
- 提取 EGO 饰品、武器、护甲数据
- 输出为可读的文本格式

## 运行环境
- Python 版本 >= 3.6
- 无需安装第三方依赖包

## 使用方法

1. 复制 `config.ini.example` 为 `config.ini`（或手动创建）
2. 编辑 `config.ini`，设置你的 Mod 搜索目录（详见下方配置说明）
3. 运行任意脚本，例如：
    ```bash
    python3 "1A-6-5-EGOWeaponSearchTool.py"
    ```

## 配置说明

工具通过根目录下的 `config.ini` 文件控制扫描行为。配置采用标准 INI 格式，示例内容如下：

    [CORE]
    # 必填：要扫描的模组根目录（绝对路径或相对路径）
    target_scan_path = ./my_mods

    [SCAN]
    # 可选：是否扫描原版基础装备文件（BaseEquipment.txt）
    # 默认 false（跳过），设为 true 则一并处理
    scan_original_file = true

### 配置项详解

| 配置项 | 所属节 | 说明 | 可选值 |
| :--- | :--- | :--- | :--- |
| `target_scan_path` | `[CORE]` | 指定要扫描的模组文件夹路径 | 绝对路径或相对路径（相对于脚本所在目录） |
| `scan_original_file` | `[SCAN]` | 是否处理游戏原版的 `BaseEquipment.txt` 文件 | `true` / `false`（默认 `false`，大小写不敏感） |

- 若 `config.ini` 不存在或缺少相应配置项，工具会使用默认值（`target_scan_path` 默认当前目录，`scan_original_file` 默认跳过）。
- 修改配置后，**无需重启**工具，下次扫描即生效。

## 致谢 & 辅助工具
- 部分核心逻辑与代码重构由 **Deepseek** 人工智能辅助完成。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。