from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# 模拟知识库
knowledge_base = []

@app.route('/')
def home():
    return jsonify({
        "status": "在线",
        "service": "知识库问答系统API",
        "version": "1.0",
        "endpoints": ["/upload", "/ask", "/health"]
    })

@app.route('/upload', methods=['POST'])
def upload_document():
    """上传文档（简化版）"""
    data = request.json
    if data and 'content' in data:
        knowledge_base.append(data['content'])
        return jsonify({
            "success": True,
            "message": f"文档已添加，当前有{len(knowledge_base)}个文档",
            "doc_id": len(knowledge_base)
        })
    return jsonify({"error": "没有提供内容"}), 400

@app.route('/ask', methods=['POST'])
def ask_question():
    """回答问题（简化版）"""
    data = request.json
    if not data or 'question' not in data:
        return jsonify({"error": "没有提供问题"}), 400
    
    question = data['question'].lower()
    
    # 简单关键词匹配
    for doc in knowledge_base:
        if any(word in doc.lower() for word in question.split()):
            return jsonify({
                "answer": f"找到相关信息：{doc[:100]}...",
                "source": "本地知识库"
            })
    
    return jsonify({
        "answer": "抱歉，知识库中没有找到相关信息",
        "suggestion": "请先上传相关文档"
    })

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "documents_count": len(knowledge_base),
        "timestamp": os.environ.get('RAILWAY_DEPLOYMENT_ID', 'local')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
