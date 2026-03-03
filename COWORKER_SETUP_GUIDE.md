# ServiceNow MCP Server - Coworker Setup Guide

Welcome! This guide will help you set up the ServiceNow MCP server on your machine in ~10 minutes.

## 🎯 What You'll Get

**73+ tools** for ServiceNow operations:
- 🤖 AI Agent building and debugging
- 📊 Performance analysis
- 🎫 Incident management
- 🛒 Service catalog ordering
- ✅ Pre-flight validation
- 📎 Attachment management
- 👍 Approval workflows
- And much more!

---

## ⚡ Quick Setup (5 Steps)

### Step 1: Clone the Repository

```bash
cd ~/Documents  # Or your preferred location
git clone https://github.com/mwdandr0/servicenow-mcp-server.git
cd servicenow-mcp-server
```

---

### Step 2: Install Dependencies

```bash
pip install mcp requests python-dotenv
```

**Or if you have Python 3:**
```bash
pip3 install mcp requests python-dotenv
```

---

### Step 3: Configure Your ServiceNow Credentials

**Create your `.env` file:**

```bash
cp .env.template .env
nano .env  # Or use any text editor
```

**Fill in YOUR ServiceNow credentials:**

```env
# Your ServiceNow instance (without https://)
SERVICENOW_INSTANCE=your-instance.service-now.com

# Your ServiceNow username
SERVICENOW_USERNAME=your.username

# Your ServiceNow password
SERVICENOW_PASSWORD=your-password
```

**Save and close the file.**

⚠️ **IMPORTANT:**
- Use YOUR OWN ServiceNow credentials (not the original creator's!)
- Never commit the `.env` file to Git (it's already in `.gitignore`)
- For production, create a dedicated service account

---

### Step 4: Test the MCP Server

```bash
python server.py
# Or: python3 server.py
```

**Expected output:**
```
ServiceNow MCP Server started
73 tools loaded
Waiting for requests...
```

**Press Ctrl+C to stop** (we're just testing it works)

---

### Step 5: Configure Claude Desktop

**Find your Claude Desktop config file:**

**macOS:**
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Add this configuration:**

```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python3",
      "args": ["/FULL/PATH/TO/servicenow-mcp-server/server.py"]
    }
  }
}
```

**⚠️ IMPORTANT:** Replace `/FULL/PATH/TO/` with your actual path!

**Example:**
```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python3",
      "args": ["/Users/yourname/Documents/servicenow-mcp-server/server.py"]
    }
  }
}
```

**Save the file.**

---

### Step 6: Restart Claude Desktop

1. Quit Claude Desktop completely
2. Relaunch it
3. Open a new conversation

---

## ✅ Verify It's Working

**In Claude Desktop, try these commands:**

### Test 1: Health Check
```
Run a health check on my ServiceNow instance
```

Expected: Connection verified, role information, table access report

### Test 2: List Tools
```
What ServiceNow tools do you have available?
```

Expected: List of 73+ tools

### Test 3: Query Incidents
```
Show me recent incidents
```

Expected: List of incidents from your ServiceNow instance

---

## 📚 What's Included

### Documentation Files:
- **README.md** - Complete tool reference
- **AI_AGENT_GUIDE.md** - Build AI Agents
- **PERFORMANCE_ANALYSIS_GUIDE.md** - Analyze conversation performance
- **PHASE_0_QUICK_WINS.md** - Platform utilities
- **PHASE_1_COMPLETE.md** - ITSM tools
- **PHASE_1_5_COMPLETE.md** - Pre-flight validation
- **ATTACHMENT_SIZE_LIMITS.md** - File upload guide
- **CLAUDE.md** - Persistent instructions for Claude

---

## 🎯 Example Use Cases

### Create an Incident
```
Create a P2 incident for email server slow performance
```

Claude will:
- Ask for missing mandatory fields
- Validate data before submission
- Create the incident
- Report back the incident number

### Order from Catalog
```
Order a laptop for john.doe@example.com
```

Claude will:
- Ask who it's for (already provided!)
- Search catalog items
- Show options and pricing
- Validate required fields
- Submit the order

### Analyze AI Agent Performance
```
Analyze the performance of my AI Agent conversation abc123
```

Claude will:
- Load 13+ ServiceNow tables
- Calculate durations
- Identify bottlenecks
- Provide recommendations

---

## 🔒 Security Best Practices

### DO:
- ✅ Use your own ServiceNow credentials
- ✅ Create a dedicated service account (not your personal account)
- ✅ Grant only necessary permissions
- ✅ Keep `.env` file secure (never commit it!)
- ✅ Rotate credentials periodically

### DON'T:
- ❌ Share your `.env` file with others
- ❌ Commit `.env` to version control
- ❌ Use production admin credentials for testing
- ❌ Share credentials in Slack/email/screenshots

---

## 🆘 Troubleshooting

### Issue: "Command not found: python3"

**Solution:** Try `python` instead:
```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

### Issue: "Module not found: mcp"

**Solution:** Install dependencies:
```bash
pip3 install mcp requests python-dotenv
```

### Issue: "Connection failed" or "Authentication failed"

**Solution:** Check your `.env` file:
- Is the instance URL correct?
- Are credentials correct?
- Is the instance accessible from your network?

### Issue: "Permission denied" errors

**Solution:** Check ServiceNow roles:
- Your account needs: `itil`, `sn_aia.admin`, `catalog_admin`
- Ask your ServiceNow admin to grant these roles

### Issue: Claude Desktop doesn't see the tools

**Solution:**
1. Check `claude_desktop_config.json` path is absolute (not relative)
2. Restart Claude Desktop completely
3. Check MCP server logs for errors

---

## 💡 Pro Tips

### 1. Use Auto-Completion
Claude will suggest tool names as you type ServiceNow queries.

### 2. Ask for Validation
```
Before creating this incident, validate the data first
```

### 3. Batch Operations
```
List all critical incidents, then analyze each one
```

### 4. Chained Workflows
```
Create an incident, add a work note, then upload an attachment
```

### 5. Natural Language
No need to memorize tool names! Just ask naturally:
- "What incidents are unassigned?"
- "Show me my pending approvals"
- "Create a change request for database patching"

---

## 🚀 Advanced: Horizon Deployment (Optional)

Want to host the MCP server in the cloud? See the main README for Prefect Horizon deployment instructions.

---

## 📞 Getting Help

### Resources:
- **GitHub Issues:** https://github.com/mwdandr0/servicenow-mcp-server/issues
- **Original Creator:** Ask Daniel Andrews
- **ServiceNow Docs:** https://docs.servicenow.com
- **MCP Documentation:** https://github.com/anthropics/mcp

### Common Questions:

**Q: Can I use this with my production ServiceNow instance?**
A: Yes, but use a dedicated service account with limited permissions.

**Q: Does this modify ServiceNow data?**
A: Only if you use create/update/delete tools. Read-only queries are safe.

**Q: How much does this cost?**
A: Free! It's open source. You just need ServiceNow access and Claude Desktop.

**Q: Can I customize the tools?**
A: Yes! Fork the repo and modify `server.py`. See the code - it's well documented.

---

## 🎉 You're All Set!

You now have a comprehensive ServiceNow automation toolkit integrated with Claude Desktop!

**Next Steps:**
1. Run the health check to verify everything works
2. Try creating a test incident
3. Explore the 73+ tools available
4. Read the documentation guides for specific features

**Welcome to the ServiceNow MCP community!** 🚀

---

## 📊 What You Have Now

- ✅ 73+ ServiceNow tools
- ✅ AI Agent building capabilities
- ✅ Performance analysis tools
- ✅ ITSM automation
- ✅ Pre-flight validation
- ✅ Complete documentation
- ✅ Production-ready code

**Built by Daniel Andrews with Claude Sonnet 4.5** ❤️
