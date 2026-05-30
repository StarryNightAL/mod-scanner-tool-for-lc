# ego_armor_search_tool.py
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import subprocess
from typing import Dict, List, Tuple, Optional, Any
import common   # 导入公共模块

# ==================== 保留特有函数 ====================
def extract_resistance_info(armor_content):
    """从护甲内容中提取伤害抗性信息"""
    resistances = {
        'red_res': "N/A",
        'white_res': "N/A",
        'black_res': "N/A",
        'pale_res': "N/A"
    }
    defense_pattern = r'<defenseElement\s+type="([RWBP])">([^<]+)</defenseElement>'
    defense_matches = re.findall(defense_pattern, armor_content, re.IGNORECASE)
    for defense_type, defense_value in defense_matches:
        defense_type = defense_type.upper()
        if defense_type == 'R':
            resistances['red_res'] = defense_value.strip()
        elif defense_type == 'W':
            resistances['white_res'] = defense_value.strip()
        elif defense_type == 'B':
            resistances['black_res'] = defense_value.strip()
        elif defense_type == 'P':
            resistances['pale_res'] = defense_value.strip()
    if all(value == "N/A" for value in resistances.values()):
        red_res_match = re.search(r'<redResist>([^<]*)</redResist>', armor_content, re.IGNORECASE)
        if red_res_match:
            resistances['red_res'] = red_res_match.group(1).strip()
        white_res_match = re.search(r'<whiteResist>([^<]*)</whiteResist>', armor_content, re.IGNORECASE)
        if white_res_match:
            resistances['white_res'] = white_res_match.group(1).strip()
        black_res_match = re.search(r'<blackResist>([^<]*)</blackResist>', armor_content, re.IGNORECASE)
        if black_res_match:
            resistances['black_res'] = black_res_match.group(1).strip()
        pale_res_match = re.search(r'<paleResist>([^<]*)</paleResist>', armor_content, re.IGNORECASE)
        if pale_res_match:
            resistances['pale_res'] = pale_res_match.group(1).strip()
    return resistances

class EGOArmorScanner:
    """EGO护甲扫描器"""
    
    def __init__(self, root_dir=None, debug=False):
        if root_dir is None:
            root_dir = common.get_search_root_from_config()
        self.root_dir = root_dir
        self.debug = debug
        self.real_root_dir = common.resolve_symlink(self.root_dir)
        self.armors = []
        self.processed_files = 0
    
    def scan_directory(self):
        """扫描目录"""
        print(f"📁 扫描目录: {self.real_root_dir}")
        print("🔍 正在搜索护甲信息...")
        self.armors = []
        self.processed_files = 0
        for root, dirs, files in os.walk(self.real_root_dir, followlinks=True):
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                file_path = os.path.join(root, file)
                if common.should_process_file(file_path):
                    armors = self.extract_armor_info(file_path)
                    if armors:
                        self.armors.extend(armors)
                        self.processed_files += 1
        print(f"✅ 处理了 {self.processed_files} 个文件，找到 {len(self.armors)} 个护甲")
        return self.armors
    
    def extract_armor_info(self, file_path):
        """从文件中提取护甲信息"""
        armors = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            armor_pattern = r'<equipment\s+id="([^"]*)"\s+type="armor">(.*?)</equipment>'
            armor_matches = re.findall(armor_pattern, content, re.DOTALL | re.IGNORECASE)
            mod_folder, mod_time, mod_folder_path = common.get_mod_folder_and_time(file_path, self.real_root_dir)
            short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
            localization_directory = common.find_localization_directory(mod_folder_path, 'cn')
            for armor_id, armor_content in armor_matches:
                grade_match = re.search(r'<grade>([^<]*)</grade>', armor_content, re.IGNORECASE)
                name_match = re.search(r'<name>([^<]*)</name>', armor_content, re.IGNORECASE)
                grade_value = grade_match.group(1).strip() if grade_match else "N/A"
                name_id = name_match.group(1).strip() if name_match else "N/A"
                mapped_grade = common.map_grade(grade_value)
                resistance_info = extract_resistance_info(armor_content)
                equipment_details = common.get_equipment_details(armor_id, mod_folder_path)
                armor_name = name_id
                if name_id != "N/A" and localization_directory:
                    parsed_name = common.parse_name_from_xmls(name_id, localization_directory, 
                                                      debug=self.debug and ("Depression" in mod_folder))
                    if parsed_name:
                        armor_name = parsed_name
                mod_time_str = common.format_mod_time(mod_time)
                armor = {
                    'id': armor_id.strip(),
                    'name': armor_name,
                    'grade': mapped_grade,
                    'red_res': resistance_info['red_res'],
                    'white_res': resistance_info['white_res'],
                    'black_res': resistance_info['black_res'],
                    'pale_res': resistance_info['pale_res'],
                    'research_cost': equipment_details['cost'],
                    'belongs_to': equipment_details['belongs_to'],
                    'mod_folder': short_mod_name,
                    'mod_time': mod_time,
                    'mod_time_str': mod_time_str,
                    'name_id': name_id
                }
                armors.append(armor)
        except Exception as e:
            if self.debug:
                print(f"❌ 处理文件时出错: {e}")
        return armors
    
    def display_results(self, mode='basic'):
        if not self.armors:
            print("❌ 未找到护甲信息")
            return
        self.armors.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
        if mode == 'basic':
            self.display_basic_info()
        elif mode == 'resistance':
            self.display_resistance_info()
        elif mode == 'research':
            self.display_research_info()
        elif mode == 'belongs':
            self.display_belongs_info()
        elif mode == 'all':
            self.display_all_info()
    
    def display_basic_info(self):
        print("\n📊 护甲基础信息:")
        print("-" * 90)
        mod_header = common.pad_text("模组", 20)
        time_header = common.pad_text("修改时间", 12)
        id_header = common.pad_text("ID", 15)
        name_header = common.pad_text("护甲名称", 25)
        grade_header = common.pad_text("等级", 8)
        print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}")
        print("-" * 90)
        for armor in self.armors:
            mod_field = common.pad_text(armor['mod_folder'], 20)
            time_field = common.pad_text(armor['mod_time_str'], 12)
            id_field = common.pad_text(armor['id'], 15)
            name_field = common.pad_text(armor['name'], 25)
            grade_field = common.pad_text(armor['grade'], 8)
            print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}")
    
    def display_resistance_info(self):
        print("\n🛡️ 护甲抗性信息:")
        print("-" * 100)
        mod_header = common.pad_text("模组", 15)
        time_header = common.pad_text("修改时间", 12)
        id_header = common.pad_text("ID", 10)
        name_header = common.pad_text("护甲名称", 20)
        grade_header = common.pad_text("等级", 8)
        red_header = common.pad_text("R", 6)
        white_header = common.pad_text("W", 6)
        black_header = common.pad_text("B", 6)
        pale_header = common.pad_text("P", 6)
        print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{red_header}{white_header}{black_header}{pale_header}")
        print("-" * 100)
        for armor in self.armors:
            mod_field = common.pad_text(armor['mod_folder'], 15)
            time_field = common.pad_text(armor['mod_time_str'], 12)
            id_field = common.pad_text(armor['id'], 10)
            name_field = common.pad_text(armor['name'], 20)
            grade_field = common.pad_text(armor['grade'], 8)
            red_field = common.pad_text(armor['red_res'], 6)
            white_field = common.pad_text(armor['white_res'], 6)
            black_field = common.pad_text(armor['black_res'], 6)
            pale_field = common.pad_text(armor['pale_res'], 6)
            print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{red_field}{white_field}{black_field}{pale_field}")
    
    def display_research_info(self):
        print("\n🔬 护甲研发信息:")
        print("-" * 90)
        mod_header = common.pad_text("模组", 20)
        time_header = common.pad_text("修改时间", 12)
        id_header = common.pad_text("ID", 15)
        name_header = common.pad_text("护甲名称", 25)
        grade_header = common.pad_text("等级", 8)
        cost_header = common.pad_text("研发所需", 12)
        print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{cost_header}")
        print("-" * 90)
        for armor in self.armors:
            mod_field = common.pad_text(armor['mod_folder'], 20)
            time_field = common.pad_text(armor['mod_time_str'], 12)
            id_field = common.pad_text(armor['id'], 15)
            name_field = common.pad_text(armor['name'], 25)
            grade_field = common.pad_text(armor['grade'], 8)
            cost_field = common.pad_text(armor['research_cost'], 12)
            print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{cost_field}")
    
    def display_belongs_info(self):
        print("\n👥 护甲所属信息:")
        print("-" * 110)
        mod_header = common.pad_text("模组", 20)
        time_header = common.pad_text("修改时间", 12)
        id_header = common.pad_text("ID", 15)
        name_header = common.pad_text("护甲名称", 25)
        belongs_header = common.pad_text("所属生物", 20)
        grade_header = common.pad_text("等级", 8)
        cost_header = common.pad_text("研发所需", 12)
        print(f"{mod_header}{time_header}{id_header}{name_header}{belongs_header}{grade_header}{cost_header}")
        print("-" * 110)
        for armor in self.armors:
            mod_field = common.pad_text(armor['mod_folder'], 20)
            time_field = common.pad_text(armor['mod_time_str'], 12)
            id_field = common.pad_text(armor['id'], 15)
            name_field = common.pad_text(armor['name'], 25)
            belongs_field = common.pad_text(armor['belongs_to'], 20)
            grade_field = common.pad_text(armor['grade'], 8)
            cost_field = common.pad_text(armor['research_cost'], 12)
            print(f"{mod_field}{time_field}{id_field}{name_field}{belongs_field}{grade_field}{cost_field}")
    
    def display_all_info(self):
        print("\n📋 护甲完整信息:")
        print("-" * 120)
        headers = [
            common.pad_text("模组", 15),
            common.pad_text("ID", 10),
            common.pad_text("护甲名称", 20),
            common.pad_text("等级", 6),
            common.pad_text("R", 6),
            common.pad_text("W", 6),
            common.pad_text("B", 6),
            common.pad_text("P", 6),
            common.pad_text("研发", 6),
            common.pad_text("所属", 15)
        ]
        print("".join(headers))
        print("-" * 120)
        for armor in self.armors:
            fields = [
                common.pad_text(armor['mod_folder'], 15),
                common.pad_text(armor['id'], 10),
                common.pad_text(armor['name'], 20),
                common.pad_text(armor['grade'], 6),
                common.pad_text(armor['red_res'], 6),
                common.pad_text(armor['white_res'], 6),
                common.pad_text(armor['black_res'], 6),
                common.pad_text(armor['pale_res'], 6),
                common.pad_text(armor['research_cost'], 6),
                common.pad_text(armor['belongs_to'], 15)
            ]
            print("".join(fields))
    
    def export_results(self, filename="ego_armors_export.txt"):
        if not self.armors:
            print("❌ 没有数据可导出")
            return False
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("EGO护甲信息导出\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"扫描目录: {self.real_root_dir}\n")
                f.write(f"找到护甲数量: {len(self.armors)}\n")
                f.write("=" * 100 + "\n\n")
                for armor in self.armors:
                    f.write(f"护甲ID: {armor['id']}\n")
                    f.write(f"名称: {armor['name']}\n")
                    f.write(f"模组: {armor['mod_folder']}\n")
                    f.write(f"等级: {armor['grade']}\n")
                    f.write(f"红伤抗性(R): {armor['red_res']}\n")
                    f.write(f"白伤抗性(W): {armor['white_res']}\n")
                    f.write(f"黑伤抗性(B): {armor['black_res']}\n")
                    f.write(f"蓝伤抗性(P): {armor['pale_res']}\n")
                    f.write(f"研发所需: {armor['research_cost']}\n")
                    f.write(f"所属: {armor['belongs_to']}\n")
                    f.write("-" * 50 + "\n")
            print(f"✅ 结果已导出到: {filename}")
            return True
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False

def batch_process_directories(directories):
    all_results = []
    for i, directory in enumerate(directories, 1):
        print(f"\n📂 处理目录 {i}/{len(directories)}: {directory}")
        if not os.path.exists(directory):
            print(f"❌ 目录不存在: {directory}")
            continue
        scanner = EGOArmorScanner(directory)
        scanner.scan_directory()
        if scanner.armors:
            all_results.extend(scanner.armors)
            print(f"✅ 找到 {len(scanner.armors)} 个护甲")
        else:
            print("❌ 未找到护甲")
    return all_results

def interactive_main():
    scanner = None
    SEARCH_MODES = {
        '1': {'name': '基础信息', 'desc': '显示护甲基本属性（名称、等级）'},
        '2': {'name': '抗性信息', 'desc': '显示护甲伤害抗性（RWBP）'},
        '3': {'name': '研发所需', 'desc': '显示护甲研发所需cost'},
        '4': {'name': '所属信息', 'desc': '显示护甲所属生物信息'},
        '5': {'name': '综合信息', 'desc': '显示所有可用信息'},
        '6': {'name': '批量处理', 'desc': '批量处理多个模组文件夹'},
        '7': {'name': '导出结果', 'desc': '将搜索结果导出到文件'}
    }
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')
    def print_banner():
        clear_screen()
        print("=" * 80)
        print("🎮 EGO护甲搜索工具 - 交互式版本")
        print("=" * 80)
        print("🔍 功能: 扫描模组文件夹，提取EGO护甲信息")
        print("📁 支持: 自动解析本地化文本、伤害抗性、研发所需、所属生物")
        print("=" * 80)
    def print_menu():
        print("\n📋 主菜单:")
        print("-" * 40)
        for key, mode in SEARCH_MODES.items():
            print(f"  {key}. {mode['name']} - {mode['desc']}")
        print("  Q. 退出程序")
        print("-" * 40)
    while True:
        print_banner()
        if scanner and scanner.armors:
            print(f"📊 当前数据: {len(scanner.armors)} 个护甲 (来自: {scanner.real_root_dir})")
        print_menu()
        choice = input("\n请输入选项: ").strip().upper()
        if choice == 'Q':
            print("\n👋 感谢使用，再见！")
            break
        elif choice == '1':
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOArmorScanner()
                scanner.scan_directory()
            if scanner.armors:
                scanner.display_results('basic')
                input("\n按Enter键继续...")
        elif choice == '2':
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOArmorScanner()
                scanner.scan_directory()
            if scanner.armors:
                scanner.display_results('resistance')
                input("\n按Enter键继续...")
        elif choice == '3':
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOArmorScanner()
                scanner.scan_directory()
            if scanner.armors:
                scanner.display_results('research')
                input("\n按Enter键继续...")
        elif choice == '4':
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOArmorScanner()
                scanner.scan_directory()
            if scanner.armors:
                scanner.display_results('belongs')
                input("\n按Enter键继续...")
        elif choice == '5':
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOArmorScanner()
                scanner.scan_directory()
            if scanner.armors:
                scanner.display_results('all')
                input("\n按Enter键继续...")
        elif choice == '6':
            print("\n📁 批量处理模式")
            print("请输入要处理的目录路径（用分号 ; 分隔）:")
            directories_input = input("目录: ").strip()
            if directories_input:
                directories = [d.strip() for d in directories_input.split(';') if d.strip()]
                results = batch_process_directories(directories)
                if results:
                    scanner = EGOArmorScanner()
                    scanner.armors = results
                    scanner.processed_files = len(results)
                    display_choice = input("\n显示结果？(1-基础/2-抗性/3-研发/4-所属/5-全部/n-跳过): ").strip()
                    if display_choice in ('1', '2', '3', '4', '5'):
                        modes = {'1': 'basic', '2': 'resistance', '3': 'research', '4': 'belongs', '5': 'all'}
                        scanner.display_results(modes[display_choice])
                input("\n按Enter键继续...")
        elif choice == '7':
            if not scanner or not scanner.armors:
                print("❌ 没有数据可导出")
                input("按Enter键继续...")
                continue
            filename = input(f"导出文件名 (默认: ego_armors_export.txt): ").strip()
            if not filename:
                filename = "ego_armors_export.txt"
            scanner.export_results(filename)
            input("按Enter键继续...")
        else:
            print("❌ 无效选项")
            input("按Enter键继续...")

def quick_search(mode='basic', directory=None, export=False):
    if directory is None:
        directory = common.get_search_root_from_config()
    scanner = EGOArmorScanner(directory)
    scanner.scan_directory()
    if scanner.armors:
        if mode == 'basic':
            scanner.display_results('basic')
        elif mode == 'resistance':
            scanner.display_results('resistance')
        elif mode == 'research':
            scanner.display_results('research')
        elif mode == 'belongs':
            scanner.display_results('belongs')
        elif mode == 'all':
            scanner.display_results('all')
        if export:
            scanner.export_results()
    return scanner.armors

def show_help():
    print("=" * 80)
    print("🎮 EGO护甲搜索工具 - 帮助")
    print("=" * 80)
    print("\n📖 使用说明:")
    print("-" * 40)
    print("1. 交互模式: python ego_armor_search_tool.py")
    print("2. 快速模式: python ego_armor_search_tool.py [模式] [目录]")
    print("\n📊 可用模式:")
    print("  basic     - 基础信息")
    print("  resistance - 抗性信息")
    print("  research  - 研发信息")
    print("  belongs   - 所属信息")
    print("  all       - 全部信息")
    print("\n📁 示例:")
    print("  python ego_armor_search_tool.py basic")
    print("  python ego_armor_search_tool.py resistance ./my_mods")
    print("  python ego_armor_search_tool.py all --export")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EGO护甲搜索工具")
    parser.add_argument('mode', nargs='?', default='interactive', 
                       help='搜索模式: basic, resistance, research, belongs, all, interactive')
    parser.add_argument('directory', nargs='?', default=None, 
                       help='搜索目录 (默认为当前目录)')
    parser.add_argument('--export', action='store_true', 
                       help='导出结果到文件')
    parser.add_argument('--debug', action='store_true', 
                       help='启用调试模式')
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        try:
            interactive_main()
        except KeyboardInterrupt:
            print("\n\n👋 程序已中断")
    elif args.mode in ['basic', 'resistance', 'research', 'belongs', 'all']:
        quick_search(args.mode, args.directory, args.export)
    elif args.mode == 'help':
        show_help()
    else:
        print(f"❌ 未知模式: {args.mode}")
        print("使用 'python ego_armor_search_tool.py help' 查看帮助")