# ego_weapon_search_tool.py
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import subprocess
from typing import Dict, List, Tuple, Optional, Any
import json

def get_search_root_from_config(default_root=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                path = config.get('target_scan_path')
                if path:
                    if not os.path.isabs(path):
                        path = os.path.join(script_dir, path)
                    return path
        except:
            pass
    return default_root if default_root is not None else os.getcwd()

# ==================== 公共配置和函数 ====================
GRADE_MAPPING = {
    '1': 'ZAYIN',
    '2': 'TETH', 
    '3': 'HE',
    '4': 'WAW',
    '5': 'ALEPH'
}

# 定义搜索模式
SEARCH_MODES = {
    '1': {'name': '基础信息', 'desc': '显示武器基本属性（名称、等级、攻速、距离）'},
    '2': {'name': '伤害信息', 'desc': '显示武器伤害信息（伤害类型、最小/最大伤害）'},
    '3': {'name': '研发所需', 'desc': '显示武器研发所需cost'},
    '4': {'name': '所属信息', 'desc': '显示武器所属生物信息'},
    '5': {'name': '综合信息', 'desc': '显示所有可用信息'},
    '6': {'name': '批量处理', 'desc': '批量处理多个模组文件夹'},
    '7': {'name': '导出结果', 'desc': '将搜索结果导出到文件'}
}

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """打印程序横幅"""
    clear_screen()
    print("=" * 80)
    print("🎮 EGO武器搜索工具 - 交互式版本")
    print("=" * 80)
    print("🔍 功能: 扫描模组文件夹，提取EGO武器信息")
    print("📁 支持: 自动解析本地化文本、伤害信息、研发所需、所属生物")
    print("=" * 80)

def print_menu():
    """打印主菜单"""
    print("\n📋 主菜单:")
    print("-" * 40)
    for key, mode in SEARCH_MODES.items():
        print(f"  {key}. {mode['name']} - {mode['desc']}")
    print("  Q. 退出程序")
    print("-" * 40)

def get_display_width(text):
    """计算字符串在控制台中的显示宽度"""
    if text is None:
        return 0
        
    width = 0
    for char in str(text):
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def pad_text(text, width):
    """将文本填充到指定宽度，考虑中英文字符宽度差异"""
    if text is None:
        text = ""
    text = str(text)
    current_width = get_display_width(text)
    if current_width >= width:
        return text
    return text + ' ' * (width - current_width)

def resolve_symlink(path):
    """解析符号链接，返回真实路径"""
    try:
        return os.path.realpath(path)
    except:
        return path

def should_process_file(file_path):
    """判断是否应该处理该文件"""
    filename = os.path.basename(file_path)
    
    # 跳过 BaseEquipment.txt 文件
    if filename.lower() == "baseequipment.txt":
        return False
    
    # 只处理 .txt 和 .xml 文件
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ('.txt', '.xml')

def map_grade(grade_value):
    """将数字等级映射为对应的名称"""
    grade_value = grade_value.strip() if grade_value else grade_value
    return GRADE_MAPPING.get(grade_value, grade_value)

def get_mod_folder_and_time(file_path, root_path):
    """获取文件所属的模组文件夹和修改时间"""
    try:
        real_file_path = resolve_symlink(file_path)
        real_root_path = resolve_symlink(root_path)
        
        try:
            rel_path = os.path.relpath(real_file_path, real_root_path)
        except ValueError:
            rel_path = real_file_path
        
        path_parts = rel_path.split(os.sep)
        
        if len(path_parts) > 1 and path_parts[0] not in ('..', '.'):
            mod_folder_name = path_parts[0]
            mod_folder_path = os.path.join(real_root_path, mod_folder_name)
            
            if os.path.exists(mod_folder_path):
                mod_time = os.path.getmtime(mod_folder_path)
                return mod_folder_name, mod_time, mod_folder_path
            else:
                return mod_folder_name, None, None
        else:
            return "Root", os.path.getmtime(real_file_path), real_root_path
            
    except (ValueError, OSError):
        return "Unknown", None, None

# ==================== 本地化文本解析 ====================
def find_localization_directory(mod_folder_path, preferred_lang='cn'):
    """查找本地化目录，支持多种语言"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return None
    
    # 语言优先级顺序
    language_order = [preferred_lang, 'cn', 'en', 'jp', 'kr']
    
    for lang in language_order:
        xmls_lang_path = os.path.join(mod_folder_path, "Equipment", "xmls", lang)
        if os.path.exists(xmls_lang_path) and os.path.isdir(xmls_lang_path):
            return xmls_lang_path
    
    return None

def clean_xml_tags(text):
    """清理XML/HTML标签"""
    if not text:
        return text
    
    text = re.sub(r'<color=[^>]*>', '', text)
    text = re.sub(r'</color>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()

def parse_name_from_xmls(name_id, localization_directory, debug=False):
    """从本地化目录解析名称"""
    if not localization_directory or not os.path.exists(localization_directory):
        if debug:
            print(f"调试: 本地化目录不存在: {localization_directory}")
        return None
    
    xml_files = []
    for file in os.listdir(localization_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(localization_directory, file))
    
    if not xml_files:
        return None
    
    # 解析每个XML文件
    for xml_file in xml_files:
        try:
            # 使用ElementTree解析
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                for elem in root.iter():
                    elem_id = elem.get('id')
                    if elem_id == name_id:
                        text = elem.text
                        if text:
                            return clean_xml_tags(text)
            except ET.ParseError:
                pass
            
            # 使用正则表达式作为备选
            with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                return clean_xml_tags(text)
                
        except Exception:
            continue
    
    return None

# ==================== 伤害信息提取 ====================
def extract_damage_info(weapon_content):
    """从武器内容中提取伤害信息"""
    damage_matches = re.findall(r'<damage\s+type="([^"]*)"\s+min="([^"]*)"\s+max="([^"]*)"', 
                               weapon_content, re.IGNORECASE)
    
    if damage_matches:
        damage_type = damage_matches[0][0].strip()
        damage_min = damage_matches[0][1].strip()
        damage_max = damage_matches[0][2].strip()
        return damage_type, damage_min, damage_max
    
    # 备用格式
    damage_match = re.search(r'<damage\s+([^>]*)>', weapon_content, re.IGNORECASE)
    if damage_match:
        damage_attrs = damage_match.group(1)
        type_match = re.search(r'type\s*=\s*["\']([^"\']*)["\']', damage_attrs)
        min_match = re.search(r'min\s*=\s*["\']([^"\']*)["\']', damage_attrs)
        max_match = re.search(r'max\s*=\s*["\']([^"\']*)["\']', damage_attrs)
        
        damage_type = type_match.group(1).strip() if type_match else "N/A"
        damage_min = min_match.group(1).strip() if min_match else "N/A"
        damage_max = max_match.group(1).strip() if max_match else "N/A"
        return damage_type, damage_min, damage_max
    
    return "N/A", "N/A", "N/A"

# ==================== 研发所需和所属信息 ====================
def find_stat_files(mod_folder_path):
    """查找_stat.txt文件"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return []
    
    creature_path = os.path.join(mod_folder_path, "Creature", "Creatures")
    if not os.path.exists(creature_path):
        return []
    
    stat_files = []
    for root, dirs, files in os.walk(creature_path):
        for file in files:
            if file.lower().endswith('_stat.txt'):
                stat_files.append(os.path.join(root, file))
    
    return stat_files

def parse_stat_file_for_equipment(stat_file):
    """从_stat.txt文件提取装备信息"""
    equipment_dict = {}
    script_name = None
    
    try:
        with open(stat_file, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # 提取script标签
        script_match = re.search(r'<script>([^<]+)</script>', content, re.IGNORECASE)
        if script_match:
            script_name = script_match.group(1).strip()
        
        # 匹配equipment标签
        equipment_pattern = r'<equipment\s+[^>]*?\s+equipId\s*=\s*["\']([^"\']*)["\'][^>]*?>'
        equipment_matches = re.findall(equipment_pattern, content, re.IGNORECASE)
        
        for equip_id in equipment_matches:
            pattern = rf'<equipment\s+[^>]*?\s+equipId\s*=\s*["\']{re.escape(equip_id)}["\'][^>]*?>'
            match = re.search(pattern, content, re.IGNORECASE)
            
            if match:
                equipment_tag = match.group(0)
                cost_match = re.search(r'cost\s*=\s*["\']([^"\']*)["\']', equipment_tag, re.IGNORECASE)
                cost = cost_match.group(1) if cost_match else "N/A"
                
                equipment_dict[equip_id.strip()] = {
                    'cost': cost.strip(),
                    'script_name': script_name
                }
                
    except Exception:
        pass
    
    return equipment_dict

def get_creature_info(script_name, mod_folder_path):
    """获取生物信息"""
    if not script_name or not mod_folder_path:
        return None
    
    # 查找CreatureList目录
    creature_list_path = os.path.join(mod_folder_path, "Creature", "CreatureList")
    if not os.path.exists(creature_list_path):
        return None
    
    # 查找creature ID
    creature_id = None
    for file in os.listdir(creature_list_path):
        if file.lower().endswith('.txt'):
            file_path = os.path.join(creature_list_path, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                pattern = rf'<creature\s+[^>]*?\s+name\s*=\s*["\']{re.escape(script_name)}["\'][^>]*?>'
                matches = re.findall(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    id_match = re.search(r'id\s*=\s*["\']([^"\']*)["\']', match)
                    if id_match:
                        creature_id = id_match.group(1).strip()
                        break
                        
                if creature_id:
                    break
                    
            except Exception:
                continue
    
    if not creature_id:
        return None
    
    # 查找creature名称
    creature_info_path = os.path.join(mod_folder_path, "Creature", "CreatureInfo", "cn")
    if not os.path.exists(creature_info_path):
        return None
    
    for file in os.listdir(creature_info_path):
        if file.lower().endswith(('.txt', '.xml')):
            file_path = os.path.join(creature_info_path, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                pattern = rf'<info\s+id\s*=\s*["\']{re.escape(creature_id)}["\'][^>]*?>(.*?)</info>'
                info_matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                
                if info_matches:
                    info_content = info_matches[-1]
                    name_pattern = r'<name\s+openLevel\s*=\s*["\'][^"\']*["\'][^>]*?>(.*?)</name>'
                    name_matches = re.findall(name_pattern, info_content, re.DOTALL | re.IGNORECASE)
                    
                    if name_matches:
                        return name_matches[-1].strip()
                        
            except Exception:
                continue
    
    return None

def get_equipment_details(weapon_id, mod_folder_path):
    """获取装备详细信息（研发所需和所属）"""
    if not mod_folder_path:
        return {"cost": "N/A", "belongs_to": "N/A"}
    
    stat_files = find_stat_files(mod_folder_path)
    if not stat_files:
        return {"cost": "N/A", "belongs_to": "N/A"}
    
    for stat_file in stat_files:
        equipment_dict = parse_stat_file_for_equipment(stat_file)
        
        if weapon_id in equipment_dict:
            equipment_info = equipment_dict[weapon_id]
            cost = equipment_info['cost']
            script_name = equipment_info.get('script_name')
            
            belongs_to = "N/A"
            if script_name:
                creature_name = get_creature_info(script_name, mod_folder_path)
                if creature_name:
                    belongs_to = creature_name
            
            return {"cost": cost, "belongs_to": belongs_to}
    
    return {"cost": "N/A", "belongs_to": "N/A"}

# ==================== 主搜索函数 ====================
class EGOWeaponScanner:
    """EGO武器扫描器"""
    
    def __init__(self, root_dir=None, debug=False):
        if root_dir is None:
            root_dir = get_search_root_from_config()
        self.root_dir = root_dir
        self.debug = debug
        self.real_root_dir = resolve_symlink(self.root_dir)
        self.weapons = []
        self.processed_files = 0
    
    def scan_directory(self):
        """扫描目录"""
        print(f"📁 扫描目录: {self.real_root_dir}")
        print("🔍 正在搜索武器信息...")
        
        self.weapons = []
        self.processed_files = 0
        
        for root, dirs, files in os.walk(self.real_root_dir, followlinks=True):
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = os.path.join(root, file)
                
                if should_process_file(file_path):
                    weapons = self.extract_weapon_info(file_path)
                    if weapons:
                        self.weapons.extend(weapons)
                        self.processed_files += 1
        
        print(f"✅ 处理了 {self.processed_files} 个文件，找到 {len(self.weapons)} 个武器")
        return self.weapons
    
    def extract_weapon_info(self, file_path):
        """从文件中提取武器信息"""
        weapons = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # 匹配weapon块
            weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
            weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
            
            # 获取模组信息
            mod_folder, mod_time, mod_folder_path = get_mod_folder_and_time(file_path, self.real_root_dir)
            short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
            
            # 查找本地化目录
            localization_directory = find_localization_directory(mod_folder_path, 'cn')
            
            for weapon_id, weapon_content in weapon_matches:
                # 提取基本信息
                range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
                attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
                grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
                name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
                
                range_value = range_match.group(1).strip() if range_match else "N/A"
                attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
                grade_value = grade_match.group(1).strip() if grade_match else "N/A"
                name_id = name_match.group(1).strip() if name_match else "N/A"
                
                # 映射等级
                mapped_grade = map_grade(grade_value)
                
                # 提取伤害信息
                damage_type, damage_min, damage_max = extract_damage_info(weapon_content)
                
                # 提取研发所需和所属信息
                equipment_details = get_equipment_details(weapon_id, mod_folder_path)
                
                # 解析武器名称
                weapon_name = name_id
                if name_id != "N/A" and localization_directory:
                    parsed_name = parse_name_from_xmls(name_id, localization_directory, 
                                                      debug=self.debug and ("Depression" in mod_folder))
                    if parsed_name:
                        weapon_name = parsed_name
                
                # 格式化时间
                mod_time_str = ""
                if mod_time:
                    try:
                        mod_time_str = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
                    except:
                        mod_time_str = ""
                
                # 创建武器对象
                weapon = {
                    'id': weapon_id.strip(),
                    'name': weapon_name,
                    'range': range_value,
                    'attack_speed': attack_speed_value,
                    'grade': mapped_grade,
                    'damage_type': damage_type,
                    'damage_min': damage_min,
                    'damage_max': damage_max,
                    'research_cost': equipment_details['cost'],
                    'belongs_to': equipment_details['belongs_to'],
                    'mod_folder': short_mod_name,
                    'mod_time': mod_time,
                    'mod_time_str': mod_time_str,
                    'name_id': name_id
                }
                
                weapons.append(weapon)
                
        except Exception as e:
            if self.debug:
                print(f"❌ 处理文件时出错: {e}")
        
        return weapons
    
    def display_results(self, mode='basic'):
        """显示结果"""
        if not self.weapons:
            print("❌ 未找到武器信息")
            return
        
        # 排序
        self.weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), 
                                        x['mod_folder']))
        
        # 根据模式显示
        if mode == 'basic':
            self.display_basic_info()
        elif mode == 'damage':
            self.display_damage_info()
        elif mode == 'research':
            self.display_research_info()
        elif mode == 'belongs':
            self.display_belongs_info()
        elif mode == 'all':
            self.display_all_info()
    
    def display_basic_info(self):
        """显示基础信息"""
        print("\n📊 武器基础信息:")
        print("-" * 100)
        
        mod_header = pad_text("模组", 20)
        time_header = pad_text("修改时间", 12)
        id_header = pad_text("ID", 15)
        name_header = pad_text("武器名称", 25)
        grade_header = pad_text("等级", 8)
        speed_header = pad_text("攻击速度", 12)
        range_header = pad_text("攻击距离", 8)
        
        print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{speed_header}{range_header}")
        print("-" * 100)
        
        for weapon in self.weapons:
            mod_field = pad_text(weapon['mod_folder'], 20)
            time_field = pad_text(weapon['mod_time_str'], 12)
            id_field = pad_text(weapon['id'], 15)
            name_field = pad_text(weapon['name'], 25)
            grade_field = pad_text(weapon['grade'], 8)
            speed_field = pad_text(weapon['attack_speed'], 12)
            range_field = pad_text(weapon['range'], 8)
            
            print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{speed_field}{range_field}")
    
    def display_damage_info(self):
        """显示伤害信息"""
        print("\n⚔️ 武器伤害信息:")
        print("-" * 130)
        
        mod_header = pad_text("模组", 20)
        time_header = pad_text("修改时间", 12)
        id_header = pad_text("ID", 15)
        name_header = pad_text("武器名称", 25)
        grade_header = pad_text("等级", 8)
        type_header = pad_text("伤害类型", 12)
        min_header = pad_text("最小伤害", 12)
        max_header = pad_text("最大伤害", 12)
        
        print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{type_header}{min_header}{max_header}")
        print("-" * 130)
        
        for weapon in self.weapons:
            mod_field = pad_text(weapon['mod_folder'], 20)
            time_field = pad_text(weapon['mod_time_str'], 12)
            id_field = pad_text(weapon['id'], 15)
            name_field = pad_text(weapon['name'], 25)
            grade_field = pad_text(weapon['grade'], 8)
            type_field = pad_text(weapon['damage_type'], 12)
            min_field = pad_text(weapon['damage_min'], 12)
            max_field = pad_text(weapon['damage_max'], 12)
            
            print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{type_field}{min_field}{max_field}")
    
    def display_research_info(self):
        """显示研发信息"""
        print("\n🔬 武器研发信息:")
        print("-" * 100)
        
        mod_header = pad_text("模组", 20)
        time_header = pad_text("修改时间", 12)
        id_header = pad_text("ID", 15)
        name_header = pad_text("武器名称", 25)
        grade_header = pad_text("等级", 8)
        cost_header = pad_text("研发所需", 12)
        
        print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{cost_header}")
        print("-" * 100)
        
        for weapon in self.weapons:
            mod_field = pad_text(weapon['mod_folder'], 20)
            time_field = pad_text(weapon['mod_time_str'], 12)
            id_field = pad_text(weapon['id'], 15)
            name_field = pad_text(weapon['name'], 25)
            grade_field = pad_text(weapon['grade'], 8)
            cost_field = pad_text(weapon['research_cost'], 12)
            
            print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{cost_field}")
    
    def display_belongs_info(self):
        """显示所属信息"""
        print("\n👥 武器所属信息:")
        print("-" * 120)
        
        mod_header = pad_text("模组", 20)
        time_header = pad_text("修改时间", 12)
        id_header = pad_text("ID", 15)
        name_header = pad_text("武器名称", 25)
        belongs_header = pad_text("所属生物", 20)
        grade_header = pad_text("等级", 8)
        cost_header = pad_text("研发所需", 12)
        
        print(f"{mod_header}{time_header}{id_header}{name_header}{belongs_header}{grade_header}{cost_header}")
        print("-" * 120)
        
        for weapon in self.weapons:
            mod_field = pad_text(weapon['mod_folder'], 20)
            time_field = pad_text(weapon['mod_time_str'], 12)
            id_field = pad_text(weapon['id'], 15)
            name_field = pad_text(weapon['name'], 25)
            belongs_field = pad_text(weapon['belongs_to'], 20)
            grade_field = pad_text(weapon['grade'], 8)
            cost_field = pad_text(weapon['research_cost'], 12)
            
            print(f"{mod_field}{time_field}{id_field}{name_field}{belongs_field}{grade_field}{cost_field}")
    
    def display_all_info(self):
        """显示所有信息"""
        print("\n📋 武器完整信息:")
        print("-" * 150)
        
        headers = [
            pad_text("模组", 15),
            pad_text("ID", 10),
            pad_text("武器名称", 20),
            pad_text("等级", 6),
            pad_text("攻速", 8),
            pad_text("距离", 6),
            pad_text("伤害类型", 10),
            pad_text("伤害范围", 12),
            pad_text("研发", 6),
            pad_text("所属", 15)
        ]
        
        print("".join(headers))
        print("-" * 150)
        
        for weapon in self.weapons:
            fields = [
                pad_text(weapon['mod_folder'], 15),
                pad_text(weapon['id'], 10),
                pad_text(weapon['name'], 20),
                pad_text(weapon['grade'], 6),
                pad_text(weapon['attack_speed'], 8),
                pad_text(weapon['range'], 6),
                pad_text(weapon['damage_type'], 10),
                pad_text(f"{weapon['damage_min']}-{weapon['damage_max']}", 12),
                pad_text(weapon['research_cost'], 6),
                pad_text(weapon['belongs_to'], 15)
            ]
            
            print("".join(fields))
    
    def export_results(self, filename="ego_weapons_export.txt"):
        """导出结果到文件"""
        if not self.weapons:
            print("❌ 没有数据可导出")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("EGO武器信息导出\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"扫描目录: {self.real_root_dir}\n")
                f.write(f"找到武器数量: {len(self.weapons)}\n")
                f.write("=" * 100 + "\n\n")
                
                for weapon in self.weapons:
                    f.write(f"武器ID: {weapon['id']}\n")
                    f.write(f"名称: {weapon['name']}\n")
                    f.write(f"模组: {weapon['mod_folder']}\n")
                    f.write(f"等级: {weapon['grade']}\n")
                    f.write(f"攻击速度: {weapon['attack_speed']}\n")
                    f.write(f"攻击距离: {weapon['range']}\n")
                    f.write(f"伤害: {weapon['damage_type']} {weapon['damage_min']}-{weapon['damage_max']}\n")
                    f.write(f"研发所需: {weapon['research_cost']}\n")
                    f.write(f"所属: {weapon['belongs_to']}\n")
                    f.write("-" * 50 + "\n")
            
            print(f"✅ 结果已导出到: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False

# ==================== 批量处理功能 ====================
def batch_process_directories(directories):
    """批量处理多个目录"""
    all_results = []
    
    for i, directory in enumerate(directories, 1):
        print(f"\n📂 处理目录 {i}/{len(directories)}: {directory}")
        
        if not os.path.exists(directory):
            print(f"❌ 目录不存在: {directory}")
            continue
        
        scanner = EGOWeaponScanner(directory)
        scanner.scan_directory()
        
        if scanner.weapons:
            all_results.extend(scanner.weapons)
            print(f"✅ 找到 {len(scanner.weapons)} 个武器")
        else:
            print("❌ 未找到武器")
    
    return all_results

# ==================== 交互式主程序 ====================
def interactive_main():
    """交互式主程序"""
    scanner = None
    last_results = []
    
    while True:
        print_banner()
        
        if scanner and scanner.weapons:
            print(f"📊 当前数据: {len(scanner.weapons)} 个武器 (来自: {scanner.real_root_dir})")
        
        print_menu()
        
        choice = input("\n请输入选项: ").strip().upper()
        
        if choice == 'Q':
            print("\n👋 感谢使用，再见！")
            break
        
        elif choice == '1':  # 基础信息
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOWeaponScanner()
                scanner.scan_directory()
            
            if scanner.weapons:
                scanner.display_results('basic')
                last_results = scanner.weapons
                input("\n按Enter键继续...")
        
        elif choice == '2':  # 伤害信息
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOWeaponScanner()
                scanner.scan_directory()
            
            if scanner.weapons:
                scanner.display_results('damage')
                last_results = scanner.weapons
                input("\n按Enter键继续...")
        
        elif choice == '3':  # 研发所需
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOWeaponScanner()
                scanner.scan_directory()
            
            if scanner.weapons:
                scanner.display_results('research')
                last_results = scanner.weapons
                input("\n按Enter键继续...")
        
        elif choice == '4':  # 所属信息
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOWeaponScanner()
                scanner.scan_directory()
            
            if scanner.weapons:
                scanner.display_results('belongs')
                last_results = scanner.weapons
                input("\n按Enter键继续...")
        
        elif choice == '5':  # 综合信息
            if not scanner or input("🔄 重新扫描目录？(y/n): ").lower() == 'y':
                scanner = EGOWeaponScanner()
                scanner.scan_directory()
            
            if scanner.weapons:
                scanner.display_results('all')
                last_results = scanner.weapons
                input("\n按Enter键继续...")
        
        elif choice == '6':  # 批量处理
            print("\n📁 批量处理模式")
            print("请输入要处理的目录路径（用分号 ; 分隔）:")
            directories_input = input("目录: ").strip()
            
            if directories_input:
                directories = [d.strip() for d in directories_input.split(';') if d.strip()]
                results = batch_process_directories(directories)
                
                if results:
                    scanner = EGOWeaponScanner()
                    scanner.weapons = results
                    scanner.processed_files = len(results)
                    
                    display_choice = input("\n显示结果？(1-基础/2-伤害/3-研发/4-所属/5-全部/n-跳过): ").strip()
                    if display_choice in ('1', '2', '3', '4', '5'):
                        modes = {'1': 'basic', '2': 'damage', '3': 'research', '4': 'belongs', '5': 'all'}
                        scanner.display_results(modes[display_choice])
                
                input("\n按Enter键继续...")
        
        elif choice == '7':  # 导出结果
            if not scanner or not scanner.weapons:
                print("❌ 没有数据可导出")
                input("按Enter键继续...")
                continue
            
            filename = input(f"导出文件名 (默认: ego_weapons_export.txt): ").strip()
            if not filename:
                filename = "ego_weapons_export.txt"
            
            scanner.export_results(filename)
            input("按Enter键继续...")
        
        else:
            print("❌ 无效选项")
            input("按Enter键继续...")

# ==================== 快速启动功能 ====================
def quick_search(mode='basic', directory=None, export=False):
    """快速搜索模式"""
    if directory is None:
        directory = get_search_root_from_config()
    scanner = EGOWeaponScanner(directory)
    scanner.scan_directory()
    
    if scanner.weapons:
        if mode == 'basic':
            scanner.display_results('basic')
        elif mode == 'damage':
            scanner.display_results('damage')
        elif mode == 'research':
            scanner.display_results('research')
        elif mode == 'belongs':
            scanner.display_results('belongs')
        elif mode == 'all':
            scanner.display_results('all')
        
        if export:
            scanner.export_results()
    
    return scanner.weapons

def show_help():
    """显示帮助信息"""
    print_banner()
    print("\n📖 使用说明:")
    print("-" * 40)
    print("1. 交互模式: python ego_weapon_search_tool.py")
    print("2. 快速模式: python ego_weapon_search_tool.py [模式] [目录]")
    print("\n📊 可用模式:")
    print("  basic    - 基础信息")
    print("  damage   - 伤害信息")
    print("  research - 研发信息")
    print("  belongs  - 所属信息")
    print("  all      - 全部信息")
    print("\n📁 示例:")
    print("  python ego_weapon_search_tool.py basic")
    print("  python ego_weapon_search_tool.py damage ./my_mods")
    print("  python ego_weapon_search_tool.py all --export")

# ==================== 主入口 ====================
if __name__ == "__main__":
    import argparse
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="EGO武器搜索工具")
    parser.add_argument('mode', nargs='?', default='interactive', 
                       help='搜索模式: basic, damage, research, belongs, all, interactive')
    parser.add_argument('directory', nargs='?', default=None, 
                       help='搜索目录 (默认为当前目录)')
    parser.add_argument('--export', action='store_true', 
                       help='导出结果到文件')
    parser.add_argument('--debug', action='store_true', 
                       help='启用调试模式')
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        # 交互式模式
        try:
            interactive_main()
        except KeyboardInterrupt:
            print("\n\n👋 程序已中断")
    elif args.mode in ['basic', 'damage', 'research', 'belongs', 'all']:
        # 快速搜索模式
        quick_search(args.mode, args.directory, args.export)
    elif args.mode == 'help':
        show_help()
    else:
        print(f"❌ 未知模式: {args.mode}")
        print("使用 'python ego_weapon_search_tool.py help' 查看帮助")