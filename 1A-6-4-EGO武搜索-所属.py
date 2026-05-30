import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import common   # 导入公共模块

# 注意：以下两个函数是特有路径 "Equipment/xmls/cn"，与common不同，保留
def find_xmls_cn_directory(mod_folder_path):
    """在模组文件夹中查找Equipment/xmls/cn目录"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        print(f"调试: 模组文件夹不存在: {mod_folder_path}")
        return None
    xmls_cn_path = os.path.join(mod_folder_path, "Equipment", "xmls", "cn")
    print(f"调试: 尝试查找XML目录: {xmls_cn_path}")
    if os.path.exists(xmls_cn_path) and os.path.isdir(xmls_cn_path):
        print(f"调试: 找到XML目录: {xmls_cn_path}")
        return xmls_cn_path
    else:
        print(f"调试: XML目录不存在: {xmls_cn_path}")
    return None

def parse_name_from_xmls(name_id, xmls_cn_directory, debug=False):
    """从xmls/cn目录的.xml文件中解析name_id对应的文本 - 保留特有逻辑"""
    if not xmls_cn_directory or not os.path.exists(xmls_cn_directory):
        print(f"调试: xmls/cn目录不存在: {xmls_cn_directory}")
        return None
    
    xml_files = []
    for file in os.listdir(xmls_cn_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(xmls_cn_directory, file))
    
    print(f"调试: 在 {xmls_cn_directory} 中找到 {len(xml_files)} 个XML文件")
    for f in xml_files:
        print(f"  - {os.path.basename(f)}")
    
    if len(xml_files) == 0:
        print(f"调试: 在{xmls_cn_directory}中没有找到XML文件")
        return None
    elif len(xml_files) > 1:
        if "ColoredFixerMod-ReturnoftheRedmist" not in xmls_cn_directory:
            print(f"警告: 在{xmls_cn_directory}中发现多个.xml文件，跳过名称解析")
        return None
    
    xml_file = xml_files[0]
    
    print(f"调试: 解析XML文件: {xml_file}")
    print(f"调试: 查找ID: {name_id}")
    
    try:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            print(f"调试: XML根元素: {root.tag}")
            for elem in root.iter():
                elem_id = elem.get('id')
                if elem_id == name_id:
                    text = elem.text
                    print(f"调试: 找到匹配元素 - 标签: {elem.tag}, ID: {elem_id}, 文本: {text}")
                    return text.strip() if text else None
        except ET.ParseError as e:
            print(f"调试: ElementTree解析失败: {e}")
        
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        print(f"调试: XML文件大小: {len(content)} 字符")
        
        pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            print(f"调试: 通过正则找到文本: {text}")
            return text
        
        pattern2 = rf'<[^>]+\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</[^>]+>'
        match2 = re.search(pattern2, content, re.DOTALL | re.IGNORECASE)
        if match2:
            text = match2.group(1).strip()
            print(f"调试: 通过宽泛正则找到文本: {text}")
            return text
            
        print(f"调试: 在XML文件中搜索包含'{name_id}'的行:")
        lines = content.split('\n')
        found = False
        for i, line in enumerate(lines[:50]):
            if name_id in line:
                print(f"  第{i+1}行: {line.strip()}")
                found = True
        if not found:
            print(f"  未找到包含'{name_id}'的行")
            
    except Exception as e:
        print(f"调试: 解析XML时发生错误: {e}")
    
    print(f"调试: 未找到ID为'{name_id}'的文本")
    return None

def get_creature_id_from_creature_list(script_name, mod_folder_path):
    """从Creature/CreatureList/*.txt文件中查找creature ID"""
    if not script_name or not mod_folder_path:
        print(f"调试: script_name或mod_folder_path为空")
        return None
    
    creature_list_path = os.path.join(mod_folder_path, "Creature", "CreatureList")
    print(f"调试: 尝试查找CreatureList目录: {creature_list_path}")
    
    if not os.path.exists(creature_list_path):
        print(f"调试: Creature/CreatureList目录不存在: {creature_list_path}")
        return None
    
    creature_list_files = []
    for file in os.listdir(creature_list_path):
        if file.lower().endswith('.txt'):
            creature_list_files.append(os.path.join(creature_list_path, file))
    
    print(f"调试: 在CreatureList目录中找到 {len(creature_list_files)} 个.txt文件")
    if not creature_list_files:
        print(f"调试: CreatureList目录中没有.txt文件")
        return None
    
    for file_path in creature_list_files:
        try:
            print(f"调试: 检查文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            print(f"调试: 文件大小: {len(content)} 字符")
            pattern = rf'<creature\s+[^>]*?\s+name\s*=\s*["\']{re.escape(script_name)}["\'][^>]*?>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            print(f"调试: 找到 {len(matches)} 个匹配的creature标签")
            for match in matches:
                id_match = re.search(r'id\s*=\s*["\']([^"\']*)["\']', match)
                if id_match:
                    creature_id = id_match.group(1).strip()
                    print(f"调试: 找到creature ID: {creature_id}")
                    return creature_id
        except Exception as e:
            print(f"调试: 读取文件{file_path}时发生错误: {e}")
            continue
    
    print(f"调试: 未找到name为'{script_name}'的creature标签")
    return None

def get_creature_name_from_creature_info(creature_id, mod_folder_path):
    """从Creature/CreatureInfo/cn/*.txt或*.xml文件中查找creature名称"""
    if not creature_id or not mod_folder_path:
        print(f"调试: creature_id或mod_folder_path为空")
        return None
    
    creature_info_path = os.path.join(mod_folder_path, "Creature", "CreatureInfo", "cn")
    print(f"调试: 尝试查找CreatureInfo/cn目录: {creature_info_path}")
    
    if not os.path.exists(creature_info_path):
        print(f"调试: Creature/CreatureInfo/cn目录不存在: {creature_info_path}")
        return None
    
    creature_info_files = []
    for file in os.listdir(creature_info_path):
        if file.lower().endswith('.txt') or file.lower().endswith('.xml'):
            creature_info_files.append(os.path.join(creature_info_path, file))
    
    print(f"调试: 在CreatureInfo/cn目录中找到 {len(creature_info_files)} 个文件")
    if not creature_info_files:
        print(f"调试: CreatureInfo/cn目录中没有.txt或.xml文件")
        return None
    
    for file_path in creature_info_files:
        try:
            print(f"调试: 检查文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            print(f"调试: 文件大小: {len(content)} 字符")
            pattern = rf'<info\s+id\s*=\s*["\']{re.escape(creature_id)}["\'][^>]*?>(.*?)</info>'
            info_matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            print(f"调试: 找到 {len(info_matches)} 个匹配的info标签")
            if info_matches:
                info_content = info_matches[-1]
                name_pattern = r'<name\s+openLevel\s*=\s*["\'][^"\']*["\'][^>]*?>(.*?)</name>'
                name_matches = re.findall(name_pattern, info_content, re.DOTALL | re.IGNORECASE)
                print(f"调试: 在info块中找到 {len(name_matches)} 个name标签")
                if name_matches:
                    last_name_text = name_matches[-1].strip()
                    last_name_text = re.sub(r'\s+', ' ', last_name_text)
                    print(f"调试: 最后一个name标签文本: '{last_name_text}'")
                    return last_name_text
        except Exception as e:
            print(f"调试: 读取文件{file_path}时发生错误: {e}")
            continue
    
    print(f"调试: 在所有文件中都未找到id为'{creature_id}'的info标签")
    return None

def get_equipment_info(weapon_id, mod_folder_path):
    """获取武器的研发所需cost和所属creature名称 - 保留特有调试版本"""
    print(f"\n{'='*60}")
    print(f"调试: 开始处理武器ID: {weapon_id}")
    print(f"调试: 模组文件夹: {mod_folder_path}")
    
    if not mod_folder_path:
        print(f"调试: 模组文件夹路径不存在")
        print(f"{'='*60}")
        return {"cost": "N/A", "belongs_to": "N/A"}
    
    stat_files = common.find_stat_files(mod_folder_path)
    if not stat_files:
        print(f"调试: 未找到stat文件")
        print(f"{'='*60}")
        return {"cost": "N/A", "belongs_to": "N/A"}
    
    for stat_file in stat_files:
        equipment_dict = common.parse_stat_file_for_equipment(stat_file)
        print(f"调试: 在文件{stat_file}中找到 {len(equipment_dict)} 个equipment条目")
        if weapon_id in equipment_dict:
            equipment_info = equipment_dict[weapon_id]
            cost = equipment_info['cost']
            script_name = equipment_info.get('script_name')
            print(f"调试: 匹配到武器ID {weapon_id}")
            print(f"调试: cost: {cost}, script_name: {script_name}")
            belongs_to = "N/A"
            if script_name:
                print(f"调试: 开始根据script_name '{script_name}' 查找creature")
                creature_id = get_creature_id_from_creature_list(script_name, mod_folder_path)
                if creature_id:
                    print(f"调试: 获取到的creature_id: {creature_id}")
                    creature_name = get_creature_name_from_creature_info(creature_id, mod_folder_path)
                    if creature_name:
                        print(f"调试: 获取到的creature_name: {creature_name}")
                        belongs_to = creature_name
                    else:
                        print(f"调试: 未找到creature_name")
                else:
                    print(f"调试: 未找到creature_id")
            else:
                print(f"调试: 未找到script_name")
            print(f"调试: 处理完成 - cost: {cost}, belongs_to: {belongs_to}")
            print(f"{'='*60}")
            return {"cost": cost, "belongs_to": belongs_to}
        else:
            print(f"调试: 武器ID {weapon_id} 在该stat文件中未找到匹配")
    
    print(f"调试: 在所有stat文件中均未找到武器ID {weapon_id}")
    print(f"{'='*60}")
    return {"cost": "N/A", "belongs_to": "N/A"}

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        mod_folder, mod_time, mod_folder_path = common.get_mod_folder_and_time(file_path, root_path)
        print(f"\n{'#'*60}")
        print(f"处理文件: {file_path}")
        print(f"模组: {mod_folder}")
        print(f"找到 {len(weapon_matches)} 个武器")
        print(f"{'#'*60}")
        
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        xmls_cn_directory = find_xmls_cn_directory(mod_folder_path) if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            print(f"\n--- 处理武器ID: {weapon_id} ---")
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            print(f"武器基本信息 - ID: {weapon_id}, name_id: {name_id}, grade: {grade_value}")
            mapped_grade = common.map_grade(grade_value)
            equipment_info = get_equipment_info(weapon_id, mod_folder_path)
            research_cost = equipment_info["cost"]
            belongs_to = equipment_info["belongs_to"]
            
            weapon_name = name_id
            if name_id != "N/A" and xmls_cn_directory:
                print(f"调试: 尝试解析名称ID: {name_id}")
                parsed_name = parse_name_from_xmls(name_id, xmls_cn_directory, debug=True)
                if parsed_name:
                    weapon_name = parsed_name
                    print(f"调试: 解析成功: {name_id} -> {parsed_name}")
                else:
                    print(f"调试: 解析失败: 未找到名称 '{name_id}'")
            elif name_id != "N/A":
                print(f"调试: XML目录不存在，无法解析名称")
            
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
                'research_cost': research_cost,
                'belongs_to': belongs_to,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id
            })
            
    except Exception as e:
        print(f"错误: 提取武器信息时发生错误: {e}")
    
    return weapons

def main():
    root_dir = common.get_search_root_from_config()
    real_root_dir = common.resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls/cn目录解析武器名称")
    print("从Creature/Creatures/*_stat.txt文件提取研发所需cost")
    print("追踪武器所属生物信息")
    print("注意: 已跳过ColoredFixerMod-ReturnoftheRedmist的多个XML文件警告")
    print("=" * 130)
    
    all_weapons = []
    processed_files = 0
    
    for root, dirs, files in os.walk(real_root_dir, followlinks=True):
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            if common.should_process_file(file_path):
                weapons = extract_weapon_info(file_path, real_root_dir)
                if weapons:
                    all_weapons.extend(weapons)
                    processed_files += 1
    
    print(f"\n{'='*60}")
    print(f"处理了 {processed_files} 个文件，找到 {len(all_weapons)} 个武器")
    print(f"{'='*60}")
    print()
    
    if not all_weapons:
        print("在指定文件类型中未找到武器。")
        return
    
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    mod_header = common.pad_text("模组", 20)
    time_header = common.pad_text("修改时间", 12)
    id_header = common.pad_text("ID", 15)
    name_header = common.pad_text("武器名称", 25)
    belongs_header = common.pad_text("所属", 20)
    grade_header = common.pad_text("等级", 8)
    research_header = common.pad_text("研发所需", 12)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{belongs_header}{grade_header}{research_header}")
    print("-" * 120)
    
    for weapon in all_weapons:
        mod_field = common.pad_text(weapon['mod_folder'], 20)
        time_field = common.pad_text(weapon['mod_time_str'], 12)
        id_field = common.pad_text(weapon['id'], 15)
        name_field = common.pad_text(weapon['name'], 25)
        belongs_field = common.pad_text(weapon['belongs_to'], 20)
        grade_field = common.pad_text(weapon['grade'], 8)
        research_field = common.pad_text(weapon['research_cost'], 12)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{belongs_field}{grade_field}{research_field}")

if __name__ == "__main__":
    main()