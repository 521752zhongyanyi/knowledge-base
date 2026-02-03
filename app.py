"""
知识库问答系统 - 简化版API
部署到Railway的Python Flask应用
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import hashlib
import json
from datetime import datetime

# 初始化Flask应用
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 允许所有跨域请求

# 内存存储（简化版，生产环境应使用数据库）
knowledge_base = []  # 存储文档
query_history = []   # 存储查询历史

# ==================== 辅助函数 ====================

def generate_doc_id():
    """生成文档ID"""
    return len(knowledge_base) + 1

def simple_embedding(text, dimensions=384):
    """
    简单的文本向量化函数
    替代sentence-transformers，避免大模型依赖
    """
    words = text.lower().split()[:dimensions]
    embedding = []
    
    for i, word in enumerate(words):
        # 使用MD5哈希生成伪向量值
        hash_obj = hashlib.md5(word.encode())
        hash_int = int(hash_obj.hexdigest(), 16) % 10000
        normalized = (hash_int % 1000) / 1000.0  # 归一化到0-1
        embedding.append(normalized)
    
    # 如果文本太短，填充零向量
    while len(embedding) < dimensions:
        embedding.append(0.0)
    
    return embedding[:dimensions]

def calculate_similarity(vec1, vec2):
    """计算两个向量的余弦相似度（简化版）"""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)

# ==================== API路由 ====================

@app.route('/')
def home():
    """首页 - 显示API信息"""
    return jsonify({
        "status": "online",
        "service": "知识库问答系统 API",
        "version": "1.0.0",
        "author": "521752zhongyanyi",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "首页": "/",
            "健康检查": "/health",
            "上传文档": "POST /upload",
            "提问": "POST /ask",
            "系统状态": "/status",
            "文档列表": "/documents",
            "清空缓存": "POST /clear",
            "向量测试": "/embedding_test"
        },
        "usage": "请使用POST方法上传文档和提问"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "memory_usage": len(knowledge_base),
        "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development')
    })

@app.route('/status', methods=['GET'])
def system_status():
    """系统状态信息"""
    return jsonify({
        "system": {
            "documents_count": len(knowledge_base),
            "queries_count": len(query_history),
            "average_embedding_size": 384,
            "max_documents": 1000  # 内存限制
        },
        "performance": {
            "uptime": "刚刚启动",
            "last_query": query_history[-1]['timestamp'] if query_history else "无"
        },
        "limits": {
            "max_document_size": 10000,  # 字符数
            "max_query_length": 500,
            "supported_formats": ["text", "json"]
        }
    })

@app.route('/documents', methods=['GET'])
def list_documents():
    """列出所有文档（简略信息）"""
    docs_summary = []
    for i, doc in enumerate(knowledge_base):
        docs_summary.append({
            "id": doc['id'],
            "title": doc.get('title', f"文档_{doc['id']}"),
            "content_preview": doc['content'][:100] + "..." if len(doc['content']) > 100 else doc['content'],
            "length": len(doc['content']),
            "created_at": doc.get('created_at', '未知')
        })
    
    return jsonify({
        "count": len(docs_summary),
        "documents": docs_summary
    })

@app.route('/upload', methods=['POST'])
def upload_document():
    """
    上传文档到知识库
    请求体：{"title": "文档标题", "content": "文档内容"}
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "error": "请求体为空",
                "status": "failed"
            }), 400
        
        content = data.get('content', '').strip()
        if not content:
            return jsonify({
                "error": "文档内容不能为空",
                "status": "failed"
            }), 400
        
        # 限制文档大小
        if len(content) > 10000:
            return jsonify({
                "error": "文档内容过长（最大10000字符）",
                "status": "failed"
            }), 400
        
        # 创建文档对象
        doc_id = generate_doc_id()
        document = {
            "id": doc_id,
            "title": data.get('title', f"未命名文档_{doc_id}"),
            "content": content,
            "embedding": simple_embedding(content),
            "created_at": datetime.now().isoformat(),
            "length": len(content),
            "keywords": list(set(content.lower().split()[:10]))  # 提取关键词
        }
        
        # 添加到知识库
        knowledge_base.append(document)
        
        return jsonify({
            "status": "success",
            "message": "文档上传成功",
            "document": {
                "id": doc_id,
                "title": document['title'],
                "length": document['length'],
                "created_at": document['created_at']
            },
            "statistics": {
                "total_documents": len(knowledge_base),
                "content_length": len(content)
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": f"上传失败: {str(e)}",
            "status": "error"
        }), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    """
    提问并获取答案
    请求体：{"question": "你的问题"}
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "error": "请求体为空",
                "status": "failed"
            }), 400
        
        question = data.get('question', '').strip()
        if not question:
            return jsonify({
                "error": "问题不能为空",
                "status": "failed"
            }), 400
        
        # 限制问题长度
        if len(question) > 500:
            question = question[:500]
        
        # 记录查询历史
        query_entry = {
            "question": question,
            "timestamp": datetime.now().isoformat(),
            "documents_count": len(knowledge_base)
        }
        query_history.append(query_entry)
        
        # 如果没有文档，直接返回提示
        if not knowledge_base:
            return jsonify({
                "answer": "知识库为空，请先上传文档。",
                "suggestions": ["上传相关文档后再提问"],
                "confidence": 0.0,
                "status": "no_documents"
            })
        
        # 生成问题向量
        question_embedding = simple_embedding(question)
        
        # 查找最相似的文档
        best_match = None
        best_score = 0.0
        
        for doc in knowledge_base:
            similarity = calculate_similarity(question_embedding, doc['embedding'])
            if similarity > best_score:
                best_score = similarity
                best_match = doc
        
        # 根据相似度返回答案
        if best_match and best_score > 0.1:  # 相似度阈值
            answer = f"根据文档「{best_match['title']}」找到相关信息：\n\n"
            answer += best_match['content'][:300] + ("..." if len(best_match['content']) > 300 else "")
            
            return jsonify({
                "answer": answer,
                "source": {
                    "document_id": best_match['id'],
                    "title": best_match['title'],
                    "content_preview": best_match['content'][:100] + "...",
                    "similarity_score": round(best_score, 4)
                },
                "confidence": round(best_score, 4),
                "keywords": best_match.get('keywords', []),
                "status": "success"
            })
        else:
            # 如果没有找到相关文档，使用关键词匹配作为备选
            question_keywords = set(question.lower().split())
            keyword_matches = []
            
            for doc in knowledge_base:
                doc_keywords = set(doc.get('keywords', []))
                common_keywords = question_keywords.intersection(doc_keywords)
                if common_keywords:
                    keyword_matches.append({
                        "doc": doc,
                        "common_keywords": list(common_keywords),
                        "count": len(common_keywords)
                    })
            
            if keyword_matches:
                # 按共同关键词数量排序
                keyword_matches.sort(key=lambda x: x['count'], reverse=True)
                best_keyword_match = keyword_matches[0]['doc']
                
                answer = f"根据关键词匹配找到相关文档：\n\n"
                answer += best_keyword_match['content'][:300] + "..."
                
                return jsonify({
                    "answer": answer,
                    "source": {
                        "document_id": best_keyword_match['id'],
                        "title": best_keyword_match['title'],
                        "matched_keywords": keyword_matches[0]['common_keywords'],
                        "match_type": "keyword"
                    },
                    "confidence": 0.5,  # 关键词匹配置信度较低
                    "status": "keyword_match"
                })
            else:
                return jsonify({
                    "answer": "抱歉，知识库中没有找到相关信息。\n\n建议：\n1. 上传相关文档\n2. 重新组织问题\n3. 使用更具体的关键词",
                    "suggestions": [
                        "检查文档是否相关",
                        "尝试不同的提问方式",
                        "添加更多详细描述"
                    ],
                    "confidence": 0.0,
                    "status": "no_match"
                })
        
    except Exception as e:
        return jsonify({
            "error": f"处理问题时出错: {str(e)}",
            "status": "error"
        }), 500

@app.route('/embedding_test', methods=['GET'])
def embedding_test():
    """测试向量化功能"""
    test_text = "这是一个用于测试向量化功能的示例文本，包含多个词汇。"
    embedding = simple_embedding(test_text)
    
    return jsonify({
        "test": "向量化功能测试",
        "input_text": test_text,
        "embedding": {
            "dimensions": len(embedding),
            "sample_values": embedding[:10],  # 只显示前10个值
            "statistics": {
                "min": round(min(embedding), 4),
                "max": round(max(embedding), 4),
                "mean": round(sum(embedding)/len(embedding), 4)
            }
        },
        "note": "这是一个简化版的向量化函数，实际生产建议使用专业模型"
    })

@app.route('/clear', methods=['POST'])
def clear_cache():
    """清空知识库（仅用于测试）"""
    global knowledge_base, query_history
    cleared_count = len(knowledge_base)
    
    knowledge_base = []
    query_history = []
    
    return jsonify({
        "status": "success",
        "message": f"已清空 {cleared_count} 个文档",
        "timestamp": datetime.now().isoformat()
    })

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "API端点不存在",
        "status": 404,
        "available_endpoints": [
            "/",
            "/health", 
            "/status",
            "/documents",
            "/embedding_test",
            "POST /upload",
            "POST /ask",
            "POST /clear"
        ]
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "请求方法不允许",
        "status": 405,
        "allowed_methods": ["GET", "POST"]
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "服务器内部错误",
        "status": 500,
        "message": "请稍后重试或检查服务状态"
    }), 500

# ==================== 启动应用 ====================

if __name__ == '__main__':
    # 从环境变量获取端口，Railway会自动设置PORT
    port = int(os.environ.get('PORT', 5000))
    
    print(f"""
    ============================================
    知识库问答系统 API v1.0
    启动时间: {datetime.now()}
    运行端口: {port}
    文档数量: {len(knowledge_base)}
    环境: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}
    ============================================
    """)
    
    # 启动Flask应用
    app.run(
        host='0.0.0.0',  # 监听所有网络接口
        port=port,
        debug=False  # 生产环境设为False
    )
