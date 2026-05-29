import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import configparser

def get_search_root_from_config(default_root=None):
    """从脚本所在目录的config.ini中读取target_scan_path，若失败则返回default_root"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    if os.path.isfile(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            path = config.get('CORE', 'target_scan_path', fallback=None)
            if path:
                path = path.strip()
                # 相对路径转换为相对于脚本目录的绝对路径
                if not os.path.isabs(path):
                    path = os.path.join(script_dir, path)
                return path
        except Exception:
            pass
    return default_root if default_root is not None else os.getcwd()

# 定义等级映射
GRADE_MAPPING = {
    '1': 'ZAYIN',
    '2': 'TETH', 
    '3': 'HE',
    '4': 'WAW',
    '5': 'ALEPH'
}

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
    # 先移除可能的空格
    grade_value = grade_value.strip() if grade_value else grade_value
    return GRADE_MAPPING.get(grade_value, grade_value)

def resolve_symlink(path):
    """解析符号链接，返回真实路径"""
    try:
        return os.path.realpath(path)
    except:
        return path

def get_mod_folder_and_time(file_path, root_path):
    """获取文件所属的模组文件夹和修改时间"""
    try:
        # 解析符号链接
        real_file_path = resolve_symlink(file_path)
        real_root_path = resolve_symlink(root_path)
        
        # 获取文件相对于根路径的相对路径
        try:
            rel_path = os.path.relpath(real_file_path, real_root_path)
        except ValueError:
            # 如果不在同一驱动器，尝试直接使用绝对路径
            rel_path = real_file_path
        
        # 分割相对路径，第一个部分应该是模组文件夹名
        path_parts = rel_path.split(os.sep)
        
        if len(path_parts) > 1 and path_parts[0] != '..' and path_parts[0] != '.':
            mod_folder_name = path_parts[0]
            mod_folder_path = os.path.join(real_root_path, mod_folder_name)
            
            # 获取模组文件夹的修改时间
            if os.path.exists(mod_folder_path):
                mod_time = os.path.getmtime(mod_folder_path)
                return mod_folder_name, mod_time, mod_folder_path
            else:
                return mod_folder_name, None, None
        else:
            # 如果文件直接在根路径下，没有模组文件夹
            return "Root", os.path.getmtime(real_file_path), real_root_path
            
    except (ValueError, OSError):
        # 如果无法获取相对路径或修改时间
        return "Unknown", None, None

def find_xmls_cn_directory(mod_folder_path):
    """在模组文件夹中查找Equipment/xmls/cn目录"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return None
    
    # 构造正确的路径: 模组文件夹/Equipment/xmls/cn
    xmls_cn_path = os.path.join(mod_folder_path, "Equipment", "xmls", "cn")
    
    if os.path.exists(xmls_cn_path) and os.path.isdir(xmls_cn_path):
        return xmls_cn_path
    
    return None

def parse_name_from_xmls(name_id, xmls_cn_directory, debug=False):
    """从xmls/cn目录的.xml文件中解析name_id对应的文本"""
    if not xmls_cn_directory or not os.path.exists(xmls_cn_directory):
        if debug:
            print(f"调试: xmls/cn目录不存在: {xmls_cn_directory}")
        return None
    
    # 收集xmls/cn目录下所有.xml文件
    xml_files = []
    for file in os.listdir(xmls_cn_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(xmls_cn_directory, file))
    
    if debug:
        print(f"调试: 在 {xmls_cn_directory} 中找到 {len(xml_files)} 个XML文件")
        for f in xml_files:
            print(f"  - {os.path.basename(f)}")
    
    # 检查.xml文件数量
    if len(xml_files) == 0:
        if debug:
            print(f"调试: 在{xmls_cn_directory}中没有找到XML文件")
        return None
    elif len(xml_files) > 1:
        # 检查是否包含ColoredFixerMod-ReturnoftheRedmist，如果是则跳过警告
        if "ColoredFixerMod-ReturnoftheRedmist" not in xmls_cn_directory:
            print(f"警告: 在{xmls_cn_directory}中发现多个.xml文件，跳过名称解析")
        return None
    
    # 只有一个.xml文件，解析它
    xml_file = xml_files[0]
    
    if debug:
        print(f"调试: 解析XML文件: {xml_file}")
        print(f"调试: 查找ID: {name_id}")
    
    try:
        # 方法1: 使用ElementTree解析
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            if debug:
                print(f"调试: XML根元素: {root.tag}")
            
            # 查找所有元素
            for elem in root.iter():
                elem_id = elem.get('id')
                if elem_id == name_id:
                    text = elem.text
                    if debug:
                        print(f"调试: 找到匹配元素 - 标签: {elem.tag}, ID: {elem_id}, 文本: {text}")
                    return text.strip() if text else None
        except ET.ParseError as e:
            if debug:
                print(f"调试: ElementTree解析失败: {e}")
        
        # 方法2: 使用正则表达式查找
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if debug:
            print(f"调试: XML文件大小: {len(content)} 字符")
            # 打印前500个字符查看文件内容
            print(f"调试: XML文件前500字符:\n{content[:500]}")
        
        # 匹配格式: <text id="ID">文本</text>
        pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            text = match.group(1).strip()
            if debug:
                print(f"调试: 通过正则找到文本: {text}")
            return text
        
        # 方法3: 尝试更宽泛的匹配
        pattern2 = rf'<[^>]+\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</[^>]+>'
        match2 = re.search(pattern2, content, re.DOTALL | re.IGNORECASE)
        
        if match2:
            text = match2.group(1).strip()
            if debug:
                print(f"调试: 通过宽泛正则找到文本: {text}")
            return text
            
        if debug:
            # 尝试查找是否有相似的内容
            print(f"调试: 在XML文件中搜索包含'{name_id}'的行:")
            lines = content.split('\n')
            for i, line in enumerate(lines[:20]):  # 只查看前20行
                if name_id in line:
                    print(f"  第{i+1}行: {line.strip()}")
            
    except Exception as e:
        if debug:
            print(f"调试: 解析XML时发生错误: {e}")
    
    if debug:
        print(f"调试: 未找到ID为'{name_id}'的文本")
    
    return None

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        # 使用正则表达式匹配weapon块
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # 获取模组文件夹和修改时间
        mod_folder, mod_time, mod_folder_path = get_mod_folder_and_time(file_path, root_path)
        
        # 截取模组文件夹名前15位
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        
        # 查找Equipment/xmls/cn目录
        xmls_cn_directory = find_xmls_cn_directory(mod_folder_path) if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            # 在weapon内容中查找range, attackSpeed, grade, name, damage
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            # 提取第一个damage标签（忽略后续的）
            damage_matches = re.findall(r'<damage\s+type="([^"]*)"\s+min="([^"]*)"\s+max="([^"]*)"', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            # 提取伤害信息，只取第一个
            if damage_matches:
                damage_type = damage_matches[0][0].strip() if damage_matches[0][0] else "N/A"
                damage_min = damage_matches[0][1].strip() if damage_matches[0][1] else "N/A"
                damage_max = damage_matches[0][2].strip() if damage_matches[0][2] else "N/A"
            else:
                # 如果没有找到damage标签，尝试其他可能的格式
                damage_match = re.search(r'<damage\s+([^>]*)>', weapon_content, re.IGNORECASE)
                if damage_match:
                    damage_attrs = damage_match.group(1)
                    type_match = re.search(r'type\s*=\s*["\']([^"\']*)["\']', damage_attrs)
                    min_match = re.search(r'min\s*=\s*["\']([^"\']*)["\']', damage_attrs)
                    max_match = re.search(r'max\s*=\s*["\']([^"\']*)["\']', damage_attrs)
                    
                    damage_type = type_match.group(1).strip() if type_match else "N/A"
                    damage_min = min_match.group(1).strip() if min_match else "N/A"
                    damage_max = max_match.group(1).strip() if max_match else "N/A"
                else:
                    damage_type = damage_min = damage_max = "N/A"
            
            # 映射等级
            mapped_grade = map_grade(grade_value)
            
            # 检查是否需要调试：Depression模组或包含"_name"的武器名称
            debug_mode = ("Depression" in mod_folder) or (name_id and re.search(r'_name', name_id))
            
            # 从xmls/cn目录解析name
            weapon_name = name_id  # 默认使用name_id
            if name_id != "N/A" and xmls_cn_directory:
                if debug_mode:
                    print(f"\n=== 调试 {mod_folder} ===")
                    print(f"武器ID: {weapon_id}")
                    print(f"名称ID: {name_id}")
                    print(f"XML目录: {xmls_cn_directory}")
                
                parsed_name = parse_name_from_xmls(name_id, xmls_cn_directory, debug=debug_mode)
                if parsed_name:
                    weapon_name = parsed_name
                    if debug_mode:
                        print(f"解析成功: {name_id} -> {parsed_name}")
                elif debug_mode:
                    print(f"解析失败: 未找到名称 '{name_id}'")
            elif name_id != "N/A" and debug_mode:
                # 没有xmls/cn目录，但需要调试
                print(f"\n=== 调试 {mod_folder} ===")
                print(f"武器ID: {weapon_id}")
                print(f"名称ID: {name_id}")
                print(f"XML目录: 不存在")
            
            # 格式化修改时间
            mod_time_str = ""
            if mod_time:
                try:
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
                except:
                    mod_time_str = ""
            
            weapons.append({
                'id': weapon_id.strip(),
                'name': weapon_name,
                'range': range_value,  # 保留但不显示
                'attackSpeed': attack_speed_value,  # 保留但不显示
                'damage_type': damage_type,
                'damage_min': damage_min,
                'damage_max': damage_max,
                'grade': mapped_grade,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id  # 保留原始的name_id用于调试
            })
            
    except Exception as e:
        # 静默处理所有错误
        pass
    
    return weapons

def get_display_width(text):
    """计算字符串在控制台中的显示宽度"""
    if text is None:
        return 0
        
    width = 0
    for char in str(text):
        # 中文字符通常占2个英文字符宽度
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

def main():
    # 获取当前目录并解析符号链接
    root_dir = get_search_root_from_config()
    real_root_dir = resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls/cn目录解析武器名称")
    print("提取伤害信息（类型、最小伤害、最大伤害）")
    print("注意: 已跳过ColoredFixerMod-ReturnoftheRedmist的多个XML文件警告")
    print("-" * 130)
    
    all_weapons = []
    processed_files = 0
    
    # 递归遍历所有文件和子目录，跟随符号链接
    for root, dirs, files in os.walk(real_root_dir, followlinks=True):
        # 跳过 .git 目录以提高性能
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # 检查是否应该处理该文件
            if should_process_file(file_path):
                weapons = extract_weapon_info(file_path, real_root_dir)
                if weapons:
                    all_weapons.extend(weapons)
                    processed_files += 1
    
    print(f"\n处理了 {processed_files} 个文件，找到 {len(all_weapons)} 个武器")
    print()
    
    if not all_weapons:
        print("在指定文件类型中未找到武器。")
        return
    
    # 按模组文件夹修改时间排序（越早修改的越靠前）
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    # 打印表头 - 更新为伤害信息
    mod_header = pad_text("模组", 20)
    time_header = pad_text("修改时间", 12)
    id_header = pad_text("ID", 15)
    name_header = pad_text("武器名称", 25)
    grade_header = pad_text("等级", 8)
    damage_type_header = pad_text("伤害类型", 12)
    damage_min_header = pad_text("最小伤害", 12)
    damage_max_header = pad_text("最大伤害", 12)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{damage_type_header}{damage_min_header}{damage_max_header}")
    print("-" * 130)
    
    # 打印每个weapon的信息
    for weapon in all_weapons:
        mod_field = pad_text(weapon['mod_folder'], 20)
        time_field = pad_text(weapon['mod_time_str'], 12)
        id_field = pad_text(weapon['id'], 15)
        name_field = pad_text(weapon['name'], 25)
        grade_field = pad_text(weapon['grade'], 8)
        damage_type_field = pad_text(weapon['damage_type'], 12)
        damage_min_field = pad_text(weapon['damage_min'], 12)
        damage_max_field = pad_text(weapon['damage_max'], 12)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{damage_type_field}{damage_min_field}{damage_max_field}")

if __name__ == "__main__":
    main()