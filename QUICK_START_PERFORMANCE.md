# Quick Start: Performance Analysis Tools

## 🚀 3 New Tools Added

### 1️⃣ Analyze Single Conversation
**When to use:** Troubleshoot a specific slow conversation

```
analyze_conversation_performance("conversation_sys_id")
```

**Example Claude Desktop prompt:**
```
"Analyze the performance of conversation abc123xyz and tell me what's taking the longest"
```

**What you get:**
- ✅ Timeline of all events
- ✅ Top 10 slowest operations
- ✅ Breakdown by category (LLM, Tools, API, etc.)
- ✅ Error summary
- ✅ Bottleneck identification
- ✅ Specific recommendations

---

### 2️⃣ Compare Multiple Conversations
**When to use:** A/B testing, finding outliers, comparing approaches

```
compare_conversation_performance("id1,id2,id3")
```

**Example Claude Desktop prompt:**
```
"Compare these 3 conversations: abc123, def456, ghi789
 Which one performed best and why?"
```

**What you get:**
- ✅ Side-by-side comparison table
- ✅ Rankings (fastest, slowest, most errors)
- ✅ Pattern identification
- ✅ Benchmark recommendations

---

### 3️⃣ Analyze Trends Over Time
**When to use:** Production monitoring, detecting performance degradation

```
analyze_conversation_trends(minutes_ago=1440)  # 24 hours
```

**Example Claude Desktop prompt:**
```
"Have my AI Agent conversations been getting slower over the past 24 hours?"
```

**What you get:**
- ✅ Aggregate statistics (avg, min, max, median)
- ✅ Performance over time (quartile breakdown)
- ✅ Trend alerts (degradation/improvement/stable)
- ✅ Outlier detection

---

## 💡 Common Workflows

### Workflow 1: "Why is this conversation slow?"
```
User: "Conversation abc123 took forever. What happened?"

Process:
1. analyze_conversation_performance("abc123")
2. Claude identifies bottleneck
3. Claude provides fix recommendation
```

### Workflow 2: "Did my change improve performance?"
```
User: "I changed the prompt. Did it help?
      Old: abc123
      New: def456"

Process:
1. compare_conversation_performance("abc123,def456", show_details=True)
2. Claude shows % improvement
3. Claude explains why it's faster/slower
```

### Workflow 3: "Are we having issues today?"
```
User: "Check if performance degraded in the last 6 hours"

Process:
1. analyze_conversation_trends(minutes_ago=360)
2. Claude detects 20% slowdown
3. Claude identifies root cause (e.g., slow tool)
4. You investigate and fix
```

---

## 🎯 Quick Commands for Claude Desktop

Copy-paste these into Claude Desktop:

### Basic Analysis
```
"Analyze conversation <sys_id>"
"What's the slowest operation in conversation <sys_id>?"
"Show me errors in conversation <sys_id>"
```

### Comparisons
```
"Compare conversations <id1>, <id2>, <id3>"
"Which conversation is fastest: <id1> or <id2>?"
"Show me detailed breakdown for <id1>, <id2>"
```

### Trends
```
"Check performance trends for the last 24 hours"
"Has performance degraded in the last 6 hours?"
"Show me outliers from the past hour"
"Analyze trends for the 'Customer Support' use case"
```

### Combined Workflows
```
"Find recent slow conversations and analyze the worst one"
"Compare the 5 most recent conversations"
"Show me performance trends, then analyze the slowest outlier"
```

---

## 📊 What Each Tool Returns

### analyze_conversation_performance
```
==================================================================
COMPREHENSIVE CONVERSATION PERFORMANCE ANALYSIS
==================================================================

📊 OVERALL TIMELINE
   First Event:  2024-02-14 10:23:15
   Last Event:   2024-02-14 10:23:43
   Total Duration: 28.30 seconds

📋 RECORDS LOADED BY TABLE
   Generative AI Logs: 5 records
   Tool Executions: 3 records
   Messages: 8 records
   ...

🐌 TOP 10 SLOWEST OPERATIONS
 1. [LLM        ] gpt-4-turbo | 8.50s | 2024-02-14 10:23:20
 2. [Tools      ] search_kb   | 4.20s | 2024-02-14 10:23:30
 ...

📊 PERFORMANCE BY CATEGORY
LLM          | Count:   5 | Total:  15.20s | Avg:  3.04s
Tools        | Count:   3 | Total:   8.50s | Avg:  2.83s
...

🎯 BOTTLENECK ANALYSIS
⚠️  SLOWEST OPERATION:
   LLM Call: gpt-4-turbo
   Duration: 8.50 seconds
   (Large prompt detected: 15,000 tokens)

💡 RECOMMENDATIONS
   ⚡ LLM calls are taking significant time:
      • Consider reducing prompt sizes
      • Use faster models for simple tasks
```

### compare_conversation_performance
```
==================================================================
CONVERSATION PERFORMANCE COMPARISON
==================================================================

📊 SUMMARY COMPARISON
ID                       | Total    | LLMs | LLM Time  | ...
abc123                   |   12.3s  |    3 |    8.5s   | ...
def456                   |   28.7s  |    7 |   18.2s   | ...
ghi789                   |   45.8s  |   12 |   32.1s   | ...

🏆 RANKINGS
⚡ FASTEST: abc123 (12.3s)
🐌 SLOWEST: ghi789 (45.8s)

💡 INSIGHTS
ghi789 is significantly slower than average
→ This conversation has 12 LLM calls vs avg of 7.3
→ Consider investigating conversation flow logic
```

### analyze_conversation_trends
```
==================================================================
CONVERSATION PERFORMANCE TRENDS
==================================================================

📈 AGGREGATE STATISTICS
Conversation Duration:
  Average: 18.50s
  Min: 8.20s
  Max: 52.30s
  Median: 16.80s

📊 PERFORMANCE OVER TIME
First 25%      : Avg Duration: 15.20s | Avg LLMs:  4.5 | Errors: 2
Second 25%     : Avg Duration: 16.80s | Avg LLMs:  5.2 | Errors: 3
Third 25%      : Avg Duration: 18.90s | Avg LLMs:  6.1 | Errors: 5
Last 25%       : Avg Duration: 20.10s | Avg LLMs:  6.8 | Errors: 8

⚠️  PERFORMANCE DEGRADATION DETECTED
   Recent conversations are 23% slower than earlier ones

🎯 OUTLIERS
SLOW | xyz789 | 52.30s (3.4x slower) | 2024-02-14 14:23:15
```

---

## 🔧 Setup Check

### 1. Verify tools are installed
```bash
cd /Users/daniel.andrews/.claude/mcp-servers/servicenow
python3 -m py_compile server.py
# Should output: ✅ Syntax check passed!
```

### 2. Restart MCP server
If you have Claude Desktop open, it should auto-reload.
Otherwise, restart your MCP server process.

### 3. Test in Claude Desktop
```
User: "What ServiceNow performance analysis tools do you have?"

Claude should list:
- analyze_conversation_performance
- compare_conversation_performance
- analyze_conversation_trends
```

---

## 📚 Full Documentation

See [PERFORMANCE_ANALYSIS_GUIDE.md](PERFORMANCE_ANALYSIS_GUIDE.md) for:
- Detailed parameter descriptions
- All output fields explained
- Real-world use case examples
- Troubleshooting guide
- Advanced workflows

---

## 🎯 Next Steps

1. **Get a conversation sys_id**
   ```
   "Show me recent AI Agent execution plans"
   ```

2. **Analyze it**
   ```
   "Analyze the performance of <sys_id>"
   ```

3. **Compare a few**
   ```
   "Compare the 3 most recent conversations"
   ```

4. **Track trends**
   ```
   "Check performance trends over the last week"
   ```

---

## 💡 Pro Tips

- **Chain queries:** "Find slow conversations, then analyze the slowest one"
- **Use filters:** "Analyze trends for 'Customer Support' use case only"
- **Get detailed:** Add `show_details=True` for deep dives
- **Include raw data:** Add `include_raw_data=True` for full JSON dumps
- **Time ranges:** Use `minutes_ago` to control lookback window

---

## ⚡ Performance Notes

- **Single conversation:** ~2-5 seconds (loads 13+ tables)
- **Compare 5 conversations:** ~10-15 seconds
- **Trends (50 conversations):** ~30-60 seconds

For faster results:
- Reduce `limit` parameter
- Use specific time ranges with `minutes_ago`
- Filter by `usecase_name`

---

## 🐛 Common Issues

**"Conversation not found"**
→ Make sure you're using sys_id, not display number
→ Try both sn_aia_execution_plan and sys_cs_conversation

**"No timing data"**
→ Some tables may not exist in your instance
→ Tools gracefully skip missing tables

**"Query too slow"**
→ Reduce time range or limit
→ Add use case filter

---

## 🎉 You're Ready!

Start analyzing:
```
"Analyze conversation <sys_id> and tell me what's slow"
```
