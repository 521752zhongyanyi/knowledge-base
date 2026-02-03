// 文件路径：/api/upload.js
// 功能：处理文档上传，保存到Supabase数据库

import { createClient } from '@supabase/supabase-js';

// 从Vercel环境变量获取Supabase连接信息
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

// 创建Supabase客户端（使用最高权限的service_role密钥）
const supabase = createClient(supabaseUrl, supabaseServiceKey);

export default async function handler(req, res) {
  // 只允许POST请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { title, content } = req.body;

    // 验证输入
    if (!title || !content) {
      return res.status(400).json({ 
        error: '标题和内容不能为空',
        status: 'failed' 
      });
    }

    console.log(`正在保存文档: ${title.substring(0, 50)}...`);

    // 插入数据到Supabase的`documents`表
    const { data, error } = await supabase
      .from('documents')
      .insert([{ 
        title: title.trim(), 
        content: content.trim() 
      }])
      .select() // 返回插入的数据
      .single(); // 只返回单条记录

    if (error) {
      console.error('Supabase插入错误:', error.message);
      return res.status(500).json({ 
        error: `数据库保存失败: ${error.message}`,
        status: 'failed' 
      });
    }

    // 成功响应
    res.status(200).json({
      status: 'success',
      message: '文档已成功保存到数据库！',
      document: {
        id: data.id,
        title: data.title,
        content_length: data.content.length,
        created_at: data.created_at
      },
      backend: 'vercel-supabase'
    });

  } catch (error) {
    console.error('服务器内部错误:', error);
    res.status(500).json({ 
      error: '服务器内部错误，请稍后重试',
      status: 'error' 
    });
  }
}
