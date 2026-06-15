# DeepSeek API Endpoints Reference

Balance (余额查询):
  URL: https://api.deepseek.com/user/balance
  Auth: Bearer sk-xxxxx (DEEPSEEK_API_KEY)
  Method: GET
  Response:
    {
      "is_available": true,
      "balance_infos": [{
        "currency": "CNY",
        "total_balance": "2.97",
        "granted_balance": "0.00",
        "topped_up_balance": "2.97"
      }]
    }

Models list:
  URL: https://api.deepseek.com/models
  Auth: Bearer sk-xxxxx
  Response: { "data": [{ "id": "deepseek-v4-flash" }, { "id": "deepseek-v4-pro" }] }

Chat completion:
  URL: https://api.deepseek.com/v1/chat/completions
  Auth: Bearer sk-xxxxx
  Same format as OpenAI /v1/chat/completions
  Models: deepseek-v4-flash, deepseek-v4-pro

Note: /dashboard/balance returns 404. Use /user/balance instead.
See also: Hermes env at /root/.hermes/.env, key=DEEPSEEK_API_KEY
