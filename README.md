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

1. 复制 `config.ini.example` 为 `config.ini`
2. 编辑 `config.ini`，设置你的 Mod 搜索目录
3. 运行任意脚本，例如：
   ```bash
   python3 "1A-6-5-EGOWeaponSearchTool.py"
   ```
   
## 致谢 & 辅助工具
- 部分核心逻辑与代码重构由 **Deepseek** 人工智能辅助完成。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。