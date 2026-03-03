# ServiceNow MCP Server

A comprehensive Model Context Protocol (MCP) server for ServiceNow, enabling Claude Desktop and other MCP clients to interact with ServiceNow instances programmatically.

## 🌟 Features

### 🤖 AI Agent Development (50+ tools)
- Build, configure, and manage ServiceNow AI Agents
- Debug agent executions and conversations
- Analyze performance bottlenecks
- Track LLM calls, tool executions, and workflows

### 📊 Performance Analysis
- Analyze conversation performance (replicates Chrome extension functionality)
- Compare multiple conversations side-by-side
- Track performance trends over time
- Identify bottlenecks across 13+ ServiceNow tables

### 🎫 ITSM Operations (13 tools)
**Incident Management:**
- Create, update, resolve incidents with auto-lookup
- Pre-built filters (critical, unassigned, breached SLA)
- Rich detail retrieval with work history

**Attachment Management:**
- Upload/download attachments (optimized for small files <5 KB)
- List and search attachments
- Note: Large files (screenshots, PDFs) should use ServiceNow UI

**Approval Management:**
- List pending approvals by state/approver/table
- Approve/reject with comments
- Full approval details with source records

### ✅ Pre-Flight Validation (2 tools)
- Discover mandatory fields (dictionary + UI policies)
- Validate record data before submission
- Prevent incomplete records due to hidden UI policy requirements

### 🛒 Service Catalog (9 tools)
- Search and browse catalog items
- Get item details with variables and pricing
- Submit orders with validation
- Track request status

### 🔧 Platform Utilities (4 tools)
- Health checks with role verification
- System properties query
- Execute any Scripted REST API (infinite extensibility)

### 📊 Generic Operations
- Query, create, update, delete records on any table
- Aggregate queries
- Flow Designer debugging
- System log queries

**Total: 73+ tools** covering the complete ServiceNow platform

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/servicenow-mcp-server.git
cd servicenow-mcp-server
```

### 2. Install Dependencies
```bash
pip install mcp requests python-dotenv
```

### 3. Configure Credentials
```bash
cp .env.template .env
```

Edit `.env` with your ServiceNow credentials:
```env
SERVICENOW_INSTANCE=dev12345.service-now.com
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password
```

### 4. Test the Server
```bash
python server.py
```

### 5. Configure Claude Desktop

Add to your Claude Desktop MCP settings:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "SERVICENOW_INSTANCE": "dev12345.service-now.com",
        "SERVICENOW_USERNAME": "your_username",
        "SERVICENOW_PASSWORD": "your_password"
      }
    }
  }
}
```

Or use the `.env` file approach:
```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

### 6. Restart Claude Desktop

The ServiceNow tools will now be available!

---

## 📚 Documentation

- **[README.md](README.md)** - Complete tool reference
- **[AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)** - Build AI Agents step-by-step
- **[PERFORMANCE_ANALYSIS_GUIDE.md](PERFORMANCE_ANALYSIS_GUIDE.md)** - Analyze conversation performance
- **[ERROR_HANDLING_STANDARD.md](ERROR_HANDLING_STANDARD.md)** - Standardized error responses
- **[ATTACHMENT_SIZE_LIMITS.md](ATTACHMENT_SIZE_LIMITS.md)** - File upload limitations and workarounds

### Phase Implementation Guides
- **[PHASE_0_QUICK_WINS.md](PHASE_0_QUICK_WINS.md)** - Platform utilities
- **[PHASE_1_COMPLETE.md](PHASE_1_COMPLETE.md)** - ITSM core tools
- **[PHASE_1_5_COMPLETE.md](PHASE_1_5_COMPLETE.md)** - Pre-flight validation

---

## 🎯 Example Usage

### Create an Incident
```
In Claude Desktop:
"Create a P1 incident for database outage affecting production"
```

Claude will:
1. Discover mandatory fields
2. Ask for missing information (caller, impact, etc.)
3. Validate data before submission
4. Create complete incident in ServiceNow

### Analyze AI Agent Performance
```
"Analyze the performance of conversation abc123 and tell me what's slow"
```

Claude will:
1. Load 13+ tables of conversation data
2. Calculate durations for all operations
3. Identify bottlenecks (LLM calls, tool executions, etc.)
4. Provide recommendations

### Order from Service Catalog
```
"Order a MacBook Pro for john.doe@example.com"
```

Claude will:
1. Search catalog for MacBook Pro
2. Get item details and variables
3. Ask for specifications (storage, RAM, etc.)
4. Validate all required fields
5. Submit order

---

## 🔒 Security

**IMPORTANT:**
- Never commit `.env` files to version control
- Use service accounts with minimum required permissions
- Consider OAuth instead of basic auth for production
- Rotate credentials regularly
- Review ServiceNow ACLs and roles

### Recommended ServiceNow Roles
- `admin` or `itil` - For ITSM operations
- `sn_aia.agent_admin` or `sn_aia.admin` - For AI Agent management
- `catalog_admin` - For catalog operations
- `attachment_admin` - For attachment management

---

## 🐛 Known Limitations

### Attachment Uploads
- **Small files (<5 KB)**: ✅ Works via MCP tool
- **Large files (>5 KB)**: ❌ Use ServiceNow UI instead
- **Reason**: MCP protocol parameter size constraints + filesystem isolation
- **See:** [ATTACHMENT_FINAL_CONCLUSION.md](ATTACHMENT_FINAL_CONCLUSION.md)

### UI Policies
- The MCP server can discover UI Policy mandatory fields
- Use `get_form_mandatory_fields` before record creation
- Prevents incomplete records from missing UI-enforced fields

---

## 🧪 Testing

### Health Check
```
In Claude Desktop:
"Run a health check on my ServiceNow instance"
```

Verifies:
- API connectivity
- Authentication
- Role permissions
- Table access
- Instance version

### Test Tools
```
"List all active AI agents"
"Show me recent incidents"
"What fields are mandatory for creating a change request?"
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

---

## 📈 Roadmap

### Completed
- ✅ AI Agent building and debugging (50+ tools)
- ✅ Performance analysis (conversation bottlenecks)
- ✅ ITSM operations (incidents, attachments, approvals)
- ✅ Pre-flight validation (mandatory field discovery)
- ✅ Service catalog ordering
- ✅ Platform utilities

### Future Enhancements
- ⏳ CMDB operations (CI management, relationships)
- ⏳ Change management workflows
- ⏳ Knowledge base operations
- ⏳ SLA and metric queries
- ⏳ Batch operations
- ⏳ Advanced Flow Designer debugging

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) by Jeff Lowin
- ServiceNow REST API documentation
- Community examples and best practices
- Extensive testing and feedback from real-world usage

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/servicenow-mcp-server/issues)
- **Documentation:** See `/docs` folder
- **ServiceNow Docs:** [ServiceNow REST API Reference](https://docs.servicenow.com/bundle/latest/page/integrate/inbound-rest/concept/c_RESTAPI.html)

---

## 🌟 Star This Repo!

If you find this MCP server useful, please give it a star ⭐ on GitHub!

---

**Built with ❤️ for the ServiceNow and Claude community**
