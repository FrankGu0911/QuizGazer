import sqlite3
import json
import csv
from datetime import datetime

def export_quiz_to_csv():
    """从quiz_history.db读取题目并导出为CSV"""
    
    # 连接数据库
    conn = sqlite3.connect('web/backend/data/quiz_history.db')
    cursor = conn.cursor()
    
    # 查询所有记录
    cursor.execute("SELECT id, timestamp, question_text, answer_text FROM quiz_records")
    records = cursor.fetchall()
    
    # 准备CSV数据
    csv_data = []
    
    for record_id, timestamp, question_text_json, answer_text in records:
        try:
            # 解析JSON
            questions = json.loads(question_text_json)
            
            # 处理每个题目
            for question in questions:
                question_type = question.get('question_type', '')
                question_text = question.get('question_text', '')
                options = question.get('options', [])
                code_block = question.get('code_block', '')
                
                # 拼接选项
                options_text = '\n'.join(options) if options else ''
                
                # 拼接完整题目
                full_question = f"{question_type}\n{question_text}"
                if code_block:
                    full_question += f"\n{code_block}"
                if options_text:
                    full_question += f"\n{options_text}"
                
                # 添加到CSV数据
                csv_data.append({
                    'record_id': record_id,
                    'timestamp': timestamp,
                    'question_type': question_type,
                    'question_text': question_text,
                    'code_block': code_block if code_block else '',
                    'options': options_text,
                    'full_question': full_question,
                    'answer_text': answer_text if answer_text else ''
                })
        
        except json.JSONDecodeError as e:
            print(f"记录 {record_id} JSON解析失败: {e}")
            continue
        except Exception as e:
            print(f"记录 {record_id} 处理失败: {e}")
            continue
    
    conn.close()
    
    # 导出CSV
    if csv_data:
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'quiz_export_{timestamp_str}.csv'
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['record_id', 'timestamp', 'question_type', 'question_text', 
                         'code_block', 'options', 'full_question', 'answer_text']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"成功导出 {len(csv_data)} 条题目到 {output_file}")
        return output_file
    else:
        print("没有找到可导出的题目")
        return None

if __name__ == '__main__':
    export_quiz_to_csv()
