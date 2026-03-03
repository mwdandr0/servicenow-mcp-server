# ServiceNow Conversation Performance Analysis Tools

## Overview

Three powerful new MCP tools have been added to analyze AI Agent conversation performance, identify bottlenecks, compare conversations, and track trends over time. These tools replicate and enhance the functionality of the Chrome extension, making performance analysis accessible through natural language in Claude Desktop.

---

## 🎯 Tool 1: `analyze_conversation_performance`

### What It Does
Loads **all 13+ ServiceNow tables** related to a conversation (just like the Chrome extension) and provides comprehensive performance analysis.

### Tables Loaded
- `sys_generative_ai_log` - LLM calls with timing
- `sys_cs_conversation_task` - Conversation tasks
- `sys_cs_message` - User/agent messages
- `sys_cs_aia_step_log` - AI Assistant step logs
- `sn_aia_execution_plan` - Agentic workflow executions
- `sn_aia_execution_task` - Individual agent tasks
- `sn_aia_message` - Agent messages
- `sn_aia_tools_execution` - Tool executions with timing
- `sys_cs_skill_discovery_tracking` - Skill discovery
- `sys_cs_fdih_invocation` - Flow Designer Hub calls
- `sys_cs_now_assist_search` - Now Assist searches
- `one_api_service_plan_invocation` - API invocations
- `one_api_service_plan_feature_invocation` - API feature invocations

### Usage

```
analyze_conversation_performance(
    conversation_sys_id="abc123xyz",
    include_raw_data=False
)
```

**Parameters:**
- `conversation_sys_id` - The sys_id of the conversation or execution plan
- `include_raw_data` - Set to `True` to include full JSON of all records (verbose)

### What You Get

1. **📊 Overall Timeline**
   - First event timestamp
   - Last event timestamp
   - Total duration in seconds/minutes

2. **📋 Record Counts**
   - Number of records loaded from each table

3. **🐌 Top 10 Slowest Operations**
   - Ranked by duration
   - Shows category, name, duration, and timestamp
   - Highlights errors

4. **📊 Performance by Category**
   - Breakdown by LLM, Tools, API, etc.
   - Total time, count, and average for each category
   - Top 3 slowest in each category

5. **❌ Error Summary**
   - All errors detected across tables
   - Error details and timing

6. **🎯 Bottleneck Analysis**
   - Identifies slowest single operation
   - Identifies slowest category overall
   - Detects time gaps (idle periods > 0.5s)

7. **💡 Recommendations**
   - Specific advice based on bottlenecks found
   - Suggestions for LLM, tool, and API optimizations

### Example Claude Desktop Usage

```
User: "Analyze the performance of conversation abc123 and tell me what's taking the longest"

Claude: [Calls analyze_conversation_performance("abc123")]

Response:
"I analyzed conversation abc123. Here's what I found:

**Total Duration:** 28.3 seconds

**Top Bottlenecks:**
1. LLM Call #3 (Question Answering) - 8.5 seconds
   - This was the slowest operation
   - It had a very large prompt (15,000 tokens)

2. Tool Execution: search_knowledge_base - 4.2 seconds
   - Second slowest operation

3. Gap of 3.1 seconds between Message #2 and LLM Call #4
   - Possible skill discovery delay

**Recommendations:**
- Reduce prompt size for LLM Call #3 to improve response time
- Consider caching knowledge base searches
- Investigate the 3.1s gap - may be unnecessary waiting"
```

---

## 🔄 Tool 2: `compare_conversation_performance`

### What It Does
Compares performance metrics across **2-10 conversations** to identify patterns, outliers, and which conversations are fastest/slowest.

### Usage

```
compare_conversation_performance(
    conversation_ids="abc123,def456,ghi789",
    show_details=False
)
```

**Parameters:**
- `conversation_ids` - Comma-separated list of conversation sys_ids (2-10)
- `show_details` - Set to `True` for detailed breakdown of each conversation

### What You Get

1. **📊 Summary Comparison Table**
   - Side-by-side comparison of all conversations
   - Shows total duration, LLM count/time, tool count/time, errors

2. **🏆 Rankings**
   - ⚡ Fastest conversation
   - 🐌 Slowest conversation
   - 💬 Most LLM calls
   - ❌ Most errors

3. **💡 Insights**
   - Average metrics across all conversations
   - Pattern identification (why is one slower?)
   - Benchmark recommendations

4. **📋 Detailed Breakdown** (if `show_details=True`)
   - Full metrics for each conversation
   - LLM and tool timing breakdown

### Example Claude Desktop Usage

```
User: "Compare these 3 conversations and tell me which one performed best:
       abc123, def456, ghi789"

Claude: [Calls compare_conversation_performance("abc123,def456,ghi789")]

Response:
"I compared the 3 conversations:

**Fastest:** def456 (12.3 seconds)
- Only 3 LLM calls, very efficient
- No errors

**Slowest:** ghi789 (45.8 seconds)
- Had 12 LLM calls vs average of 6
- Slowest LLM call took 15.2 seconds
- 3 errors occurred, possibly causing retries

**Recommendation:**
Use def456 as a performance benchmark - it's 3.7x faster than the slowest.
The high LLM call count in ghi789 suggests inefficient conversation flow."
```

---

## 📈 Tool 3: `analyze_conversation_trends`

### What It Does
Analyzes performance **trends over time** across recent conversations to detect degradation, improvements, or anomalies.

### Usage

```
analyze_conversation_trends(
    minutes_ago=1440,
    usecase_name="",
    limit=50
)
```

**Parameters:**
- `minutes_ago` - Look back this many minutes (default 1440 = 24 hours)
- `usecase_name` - Filter by specific use case/workflow (optional)
- `limit` - Maximum conversations to analyze (default 50)

### What You Get

1. **📈 Aggregate Statistics**
   - Average, min, max, median duration
   - Average LLM usage
   - Error rates

2. **📊 Performance Over Time**
   - Splits data into quartiles (first 25%, second 25%, etc.)
   - Shows if performance is degrading or improving
   - Detects trend direction

3. **⚠️ Trend Alerts**
   - "PERFORMANCE DEGRADATION DETECTED" if recent conversations are >10% slower
   - "PERFORMANCE IMPROVEMENT DETECTED" if recent conversations are >10% faster
   - "STABLE PERFORMANCE" if no significant trend

4. **🎯 Outliers**
   - Conversations significantly faster (>2x) or slower (>1.5x) than average
   - Helps identify anomalies

### Example Claude Desktop Usage

```
User: "Have my AI Agent conversations been getting slower over the past 24 hours?"

Claude: [Calls analyze_conversation_trends(minutes_ago=1440)]

Response:
"I analyzed 47 conversations from the last 24 hours. Here's what I found:

**⚠️ PERFORMANCE DEGRADATION DETECTED**

Recent conversations are 23% slower than earlier ones:
- First half average: 15.2 seconds
- Second half average: 18.7 seconds

**Outliers Found:**
- Conversation xyz789 took 52.3 seconds (3.4x slower than average)
  - This had 15 LLM calls vs average of 5
  - Occurred at 14:23 - possible system load issue?

**Recommendations:**
- Investigate why LLM call count is increasing
- Check if there were infrastructure changes around 14:00
- Consider rolling back recent changes to conversation flow"
```

---

## 🚀 Real-World Use Cases

### Use Case 1: Troubleshooting a Slow Conversation
```
User: "Conversation abc123 is really slow. Can you figure out why?"

Claude:
1. Calls analyze_conversation_performance("abc123")
2. Identifies: LLM call to "gpt-4" took 18 seconds with 20,000 token prompt
3. Recommends: "Reduce prompt size or switch to faster model for this step"
```

### Use Case 2: A/B Testing Different Approaches
```
User: "I changed my AI Agent prompt. Compare the old version (abc123)
       with the new version (def456) and tell me if it's faster"

Claude:
1. Calls compare_conversation_performance("abc123,def456", show_details=True)
2. Shows new version is 35% faster
3. Explains: "New version uses 4 LLM calls vs 7 in old version"
```

### Use Case 3: Production Monitoring
```
User: "Check if our AI Agent performance has degraded in the last 6 hours"

Claude:
1. Calls analyze_conversation_trends(minutes_ago=360, usecase_name="Customer Support")
2. Detects 15% slowdown
3. Identifies: "Tool execution: fetch_customer_data is now taking 5s vs 2s earlier"
4. Alerts you to investigate database performance
```

### Use Case 4: Finding Root Cause of Errors
```
User: "Why are we seeing so many errors in conversations today?"

Claude:
1. Calls analyze_conversation_trends(minutes_ago=1440)
2. Shows error rate increased from 2% to 15%
3. Calls analyze_conversation_performance() on a failing conversation
4. Identifies: "LLM calls failing with 'context_length_exceeded' error"
5. Recommends: "Implement prompt compression or truncation"
```

### Use Case 5: Capacity Planning
```
User: "How many LLM calls do our conversations typically make?"

Claude:
1. Calls analyze_conversation_trends(minutes_ago=10080) # 7 days
2. Reports: "Average 6.2 LLM calls per conversation"
3. Shows: "Peak usage: 12 calls, happens during complex troubleshooting flows"
4. Provides: Data for estimating API costs and capacity needs
```

---

## 🎯 How This Compares to the Chrome Extension

| Feature | Chrome Extension | MCP Tools | Advantage |
|---------|-----------------|-----------|-----------|
| Load all conversation tables | ✅ | ✅ | Same |
| Visual timeline | ✅ | ❌ | Extension |
| Timing analysis | ✅ | ✅ | Same |
| Bottleneck identification | ✅ | ✅ | Same |
| Compare multiple conversations | ❌ | ✅ | **MCP** |
| Trend analysis over time | ❌ | ✅ | **MCP** |
| Natural language queries | ❌ | ✅ | **MCP** |
| Automated recommendations | ❌ | ✅ | **MCP** |
| Access from CLI/Desktop | ❌ | ✅ | **MCP** |

**The MCP tools give you:**
- Everything the Chrome extension does for single conversations
- PLUS comparison across multiple conversations
- PLUS trend analysis over time
- PLUS natural language interface via Claude Desktop
- PLUS automated insights and recommendations

---

## 🛠️ Installation & Setup

### 1. The tools are already added to your server.py file

### 2. Restart your MCP server
```bash
cd /Users/daniel.andrews/.claude/mcp-servers/servicenow
# If running in terminal, stop and restart
# If configured in Claude Desktop, it will auto-reload
```

### 3. Verify tools are available
In Claude Desktop, try:
```
"List the available ServiceNow tools"
```

You should see:
- `analyze_conversation_performance`
- `compare_conversation_performance`
- `analyze_conversation_trends`

### 4. Start using!
```
"Analyze the performance of conversation <sys_id>"
"Compare conversations <id1>, <id2>, <id3>"
"Show me performance trends for the last 24 hours"
```

---

## 💡 Pro Tips

### 1. Get the conversation sys_id quickly
```
User: "Show me recent AI Agent conversations"
Claude: [Calls query_execution_plans()]
User: "Analyze the performance of the first one"
Claude: [Uses sys_id from previous result]
```

### 2. Chain multiple analyses
```
User: "Find the slowest conversation from the last hour,
       then analyze why it's slow"

Claude:
1. Calls analyze_conversation_trends(minutes_ago=60)
2. Identifies slowest conversation
3. Calls analyze_conversation_performance() on it
4. Provides root cause analysis
```

### 3. Compare before/after deployments
```
User: "I just deployed a new version. Compare conversations
       before the deployment (last 2 hours) vs after (last 30 min)"

Claude:
1. Gets conversation IDs from both time periods
2. Calls compare_conversation_performance()
3. Reports performance impact
```

### 4. Set up monitoring workflows
You can create custom prompts for Claude Desktop to check performance regularly:
```
"Every day, check if our AI Agent performance has degraded
 in the last 24 hours and alert me if it's >20% slower"
```

---

## 🐛 Troubleshooting

### "Conversation not found"
- Make sure you're using the sys_id, not the display number
- Try both `sn_aia_execution_plan` and `sys_cs_conversation` tables

### "No timing data available"
- Some tables may not exist in your ServiceNow instance version
- The tools gracefully skip missing tables

### "Too slow for large time ranges"
- Use smaller `minutes_ago` values
- Reduce the `limit` parameter
- Focus on specific use cases with `usecase_name` filter

---

## 📊 Output Format

All tools return **formatted text reports** optimized for Claude to read and summarize.

The reports include:
- 📊 Visual section headers
- ⚡ Performance icons
- ⚠️ Warning indicators
- ✅ Success markers
- 🎯 Bottleneck highlights
- 💡 Actionable recommendations

This makes it easy for Claude to:
1. Parse the data
2. Identify key issues
3. Provide natural language explanations
4. Suggest specific fixes

---

## 🚀 Next Steps

1. **Try it out:** Analyze a recent conversation
   ```
   "Analyze conversation <sys_id>"
   ```

2. **Compare some conversations:** Find patterns
   ```
   "Show me the 5 most recent conversations, then compare their performance"
   ```

3. **Set up monitoring:** Track trends
   ```
   "Check AI Agent performance trends over the last week"
   ```

4. **Integrate into workflows:** Use with other MCP tools
   ```
   "Find all conversations with errors in the last hour,
    then analyze the slowest one to find the root cause"
   ```

---

## 📝 Feedback & Improvements

These tools are designed to evolve. Possible future enhancements:

- [ ] Historical comparison (this week vs last week)
- [ ] Custom threshold alerts (notify if >30s)
- [ ] Integration with Splunk queries
- [ ] Cost analysis (LLM API costs per conversation)
- [ ] User-specific performance tracking
- [ ] Automated performance reports

Have ideas? Add them to the list!
