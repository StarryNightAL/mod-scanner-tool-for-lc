import os
import re
import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime

def get_search_root_from_config(default_root=None):
    """从脚本所在目录的config.json中读取target_scan_path，若失败则返回default_root"""
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
    
    if filename.lower() == "baseequipment.txt":
        return False
    
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ('.txt', '.xml')

def map_grade(grade_value):
    """将数字等级映射为对应的名称"""
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
        real_file_path = resolve_symlink(file_path)
        real_root_path = resolve_symlink(root_path)
        
        try:
            rel_path = os.path.relpath(real_file_path, real_root_path)
        except ValueError:
            rel_path = real_file_path
        
        path_parts = rel_path.split(os.sep)
        
        if len(path_parts) > 1 and path_parts[0] != '..' and path_parts[0] != '.':
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

def find_localization_directory(mod_folder_path):
    """查找本地化目录，优先cn，然后是en，最后是其他语言"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return None
    
    language_order = ['cn', 'en', 'jp', 'kr']
    
    for lang in language_order:
        xmls_lang_path = os.path.join(mod_folder_path, "Equipment", "xmls", lang)
        
        if os.path.exists(xmls_lang_path) and os.path.isdir(xmls_lang_path):
            return xmls_lang_path
    
    return None

def clean_xml_tags(text):
    """清理XML/HTML标签，如颜色标签"""
    if not text:
        return text
    
    text = re.sub(r'<color=[^>]*>', '', text)
    text = re.sub(r'</color>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()

def parse_single_xml(name_id, xml_file, debug=False):
    """解析单个XML文件，查找name_id对应的文本"""
    try:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            if debug:
                print(f"调试: 解析XML文件: {os.path.basename(xml_file)}")
                print(f"调试: XML根元素: {root.tag}")
            
            for elem in root.iter():
                elem_id = elem.get('id')
                if elem_id == name_id:
                    text = elem.text
                    if text:
                        text = clean_xml_tags(text)
                        if debug:
                            print(f"调试: 找到匹配元素 - 标签: {elem.tag}, ID: {elem_id}, 文本: {text}")
                        return text
        except ET.ParseError as e:
            if debug:
                print(f"调试: ElementTree解析失败: {e}")
        
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if debug:
            print(f"调试: XML文件大小: {len(content)} 字符")
        
        pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            text = match.group(1).strip()
            text = clean_xml_tags(text)
            if debug:
                print(f"调试: 通过正则找到文本: {text}")
            return text
        
        pattern2 = rf'<[^>]+\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</[^>]+>'
        match2 = re.search(pattern2, content, re.DOTALL | re.IGNORECASE)
        
        if match2:
            text = match2.group(1).strip()
            text = clean_xml_tags(text)
            if debug:
                print(f"调试: 通过宽泛正则找到文本: {text}")
            return text
            
    except Exception as e:
        if debug:
            print(f"调试: 解析XML时发生错误: {e}")
    
    return None

def parse_name_from_xmls(name_id, localization_directory, debug=False):
    """从本地化目录的.xml文件中解析name_id对应的文本"""
    if not localization_directory or not os.path.exists(localization_directory):
        if debug:
            print(f"调试: 本地化目录不存在: {localization_directory}")
        return None
    
    xml_files = []
    for file in os.listdir(localization_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(localization_directory, file))
    
    if debug:
        print(f"调试: 在 {localization_directory} 中找到 {len(xml_files)} 个XML文件")
    
    if len(xml_files) == 0:
        if debug:
            print(f"调试: 在{localization_directory}中没有找到XML文件")
        return None
    
    for xml_file in xml_files:
        if debug:
            print(f"调试: 尝试解析XML文件: {os.path.basename(xml_file)}")
        
        parsed_name = parse_single_xml(name_id, xml_file, debug)
        if parsed_name:
            if debug:
                print(f"调试: 在 {os.path.basename(xml_file)} 中找到匹配: {parsed_name}")
            return parsed_name
    
    if debug:
        print(f"调试: 在所有XML文件中都未找到ID为'{name_id}'的文本")
        all_ids = []
        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                id_pattern = r'id\s*=\s*["\']([^"\']+)["\']'
                ids = re.findall(id_pattern, content)
                all_ids.extend(ids)
            except:
                pass
        
        similar_ids = [id for id in all_ids if name_id.lower() in id.lower()]
        if similar_ids:
            print(f"调试: 找到相似ID: {similar_ids}")
    
    return None

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        mod_folder, mod_time, mod_folder_path = get_mod_folder_and_time(file_path, root_path)
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        localization_directory = find_localization_directory(mod_folder_path) if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            mapped_grade = map_grade(grade_value)
            
            debug_mode = ("Depression" in mod_folder) or (name_id and re.search(r'_name', name_id))
            
            weapon_name = name_id
            if name_id != "N/A" and localization_directory:
                if debug_mode:
                    print(f"\n=== 调试 {mod_folder} ===")
                    print(f"武器ID: {weapon_id}")
                    print(f"名称ID: {name_id}")
                    print(f"本地化目录: {localization_directory}")
                
                parsed_name = parse_name_from_xmls(name_id, localization_directory, debug=debug_mode)
                if parsed_name:
                    weapon_name = parsed_name
                    if debug_mode:
                        print(f"解析成功: {name_id} -> {parsed_name}")
                elif debug_mode:
                    print(f"解析失败: 未找到名称 '{name_id}'")
            elif name_id != "N/A" and debug_mode:
                print(f"\n=== 调试 {mod_folder} ===")
                print(f"武器ID: {weapon_id}")
                print(f"名称ID: {name_id}")
                print(f"本地化目录: 不存在")
            
            mod_time_str = ""
            if mod_time:
                try:
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
                except:
                    mod_time_str = ""
            
            weapons.append({
                'id': weapon_id.strip(),
                'name': weapon_name,
                'range': range_value,
                'attackSpeed': attack_speed_value,
                'grade': mapped_grade,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id
            })
            
    except Exception as e:
        pass
    
    return weapons

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

def main():
    root_dir = get_search_root_from_config()
    real_root_dir = resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls目录解析武器名称（优先cn，然后是en等语言）")
    print("-" * 120)
    
    all_weapons = []
    processed_files = 0
    
    for root, dirs, files in os.walk(real_root_dir, followlinks=True):
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            
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
    
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    mod_header = pad_text("模组", 20)
    time_header = pad_text("修改时间", 12)
    id_header = pad_text("ID", 15)
    name_header = pad_text("武器名称", 25)
    grade_header = pad_text("等级", 8)
    attack_speed_header = pad_text("攻击速度", 12)
    range_header = pad_text("攻击距离", 8)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{attack_speed_header}{range_header}")
    print("-" * 120)
    
    for weapon in all_weapons:
        mod_field = pad_text(weapon['mod_folder'], 20)
        time_field = pad_text(weapon['mod_time_str'], 12)
        id_field = pad_text(weapon['id'], 15)
        name_field = pad_text(weapon['name'], 25)
        grade_field = pad_text(weapon['grade'], 8)
        attack_speed_field = pad_text(weapon['attackSpeed'], 12)
        range_field = pad_text(weapon['range'], 8)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{attack_speed_field}{range_field}")

if __name__ == "__main__":
    main()