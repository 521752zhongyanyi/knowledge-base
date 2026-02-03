// 文件路径：/api/ask.js
// 功能：处理问答请求，从Supabase数据库检索信息

import { createClient } from '@supabase/supabase-js';

// 从Vercel环境变量获取Supabase连接信息
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

// 创建Supabase客户端
const supabase = createClient(supabaseUrl, supabaseServiceKey);

export default async function handler(req, res) {
  // 只允许POST请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { question } = req.body;

    // 验证输入
    if (!question || question.trim() === '') {
      return res.status(400).json({ 
        error: '问题不能为空',
        status: 'failed' 
      });
    }

    const searchTerm = question.trim().toLowerCase();
    console.log(`正在搜索: "${searchTerm}"`);

    // 1. 首先获取文档总数
    const { count: totalCount, error: countError } = await supabase
      .from('documents')
      .select('*', { count: 'exact', head: true });

    if (countError) {
      console.error('计数查询错误:', countError.message);
    }

    // 2. 查询数据库（使用全文搜索优化）
    const { data: documents, error: queryError } = await supabase
      .from('documents')
      .select('id, title, content, created_at')
      .or(`title.ilike.%${searchTerm}%,content.ilike.%${searchTerm}%`)
      .order('created_at', { ascending: false })
      .limit(5); // 最多返回5条最相关的

    if (queryError) {
      console.error('查询错误:', queryError.message);
      return res.status(500).json({ 
        error: `查询知识库失败: ${queryError.message}`,
        status: 'failed' 
      });
    }

    // 3. 构建响应
    let answer;
    let matchedCount = 0;

    if (documents && documents.length > 0) {
      matchedCount = documents.length;
      const primaryDoc = documents[0]; // 最相关的一条
      
      // 从内容中提取包含关键词的片段
      const contentLower = primaryDoc.content.toLowerCase();
      const termIndex = contentLower.indexOf(searchTerm);
      let contentSnippet = primaryDoc.content;
      
      if (termIndex > -1) {
        const start = Math.max(0, termIndex - 100);
        const end = Math.min(primaryDoc.content.length, termIndex + searchTerm.length + 200);
        contentSnippet = (start > 0 ? '...' : '') + 
                        primaryDoc.content.substring(start, end) + 
                        (end < primaryDoc.content.length ? '...' : '');
      } else {
        contentSnippet = primaryDoc.content.substring(0, 300) + 
                        (primaryDoc.content.length > 300 ? '...' : '');
      }
      
      answer = `根据文档《${primaryDoc.title}》：
${contentSnippet}`;
    } else if (totalCount > 0) {
      // 没有匹配项，但数据库有文档
      answer = `未在知识库中找到与"${question}"直接相关的内容。
知识库中共有 ${totalCount} 条文档，您可以尝试其他关键词或上传相关文档。`;
    } else {
      // 数据库为空
      answer = '知识库当前为空，请先上传文档。';
    }

    // 成功响应
    res.status(200).json({
      answer: answer,
      matched_count: matchedCount,
      total_documents: totalCount || 0,
      suggestions: matchedCount > 0 ? [
        '尝试更具体的关键词',
        '查看相关文档的完整内容',
        '上传更多相关文档丰富知识库'
      ] : ['上传相关文档', '尝试其他提问方式'],
      backend: 'vercel-supabase',
      response_time: Date.now() // 可用于前端计算响应时间
    });

  } catch (error) {
    console.error('服务器内部错误:', error);
    res.status(500).json({ 
      error: '处理问题时出现服务器错误',
      status: 'error',
      suggestion: '请稍后重试或检查系统状态'
    });
  }
}
