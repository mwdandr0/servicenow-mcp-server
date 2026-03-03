# ServiceNow AI Search REST API Setup

This guide will help you create a Scripted REST API in ServiceNow to expose AI Search functionality.

## Step 1: Create the Scripted REST API Service

1. **Navigate to ServiceNow**
   - Log in to your ServiceNow instance: https://demoallwf40768.service-now.com
   - Use the Application Navigator

2. **Create New REST API Service**
   - Go to: **System Web Services > Scripted REST APIs**
   - Click **New**
   - Fill in the following:
     - **Name**: `MCP AI Search API`
     - **API ID**: `mcp_ai_search` (auto-generated, you can customize)
     - **Description**: `REST API for AI Search integration with MCP server`
     - **Protection**: `--None--` (for testing, change to `Basic Auth` for production)
   - Click **Submit**

## Step 2: Create the Search Resource

1. **Open your newly created API**
   - Find `MCP AI Search API` in the list and open it

2. **In the Resources tab at the bottom, click New**

3. **Configure the Resource:**
   - **Name**: `Search`
   - **HTTP method**: `POST`
   - **Relative path**: `/search`
   - **Description**: `Execute AI Search query`

4. **Add the Script:**

Paste the following script into the **Script** field:

```javascript
(function process(/*RESTAPIRequest*/ request, /*RESTAPIResponse*/ response) {

    try {
        // Parse request body
        var requestBody = request.body.data;
        var searchQuery = requestBody.query || '';
        var configSysId = requestBody.config_sys_id || '';
        var maxResults = parseInt(requestBody.max_results) || 10;
        var disableSpellCheck = requestBody.disable_spell_check === true;

        // Validate inputs
        if (!searchQuery) {
            response.setStatus(400);
            response.setBody({
                success: false,
                error: 'Missing required parameter: query'
            });
            return;
        }

        // If no config provided, try to find the first available AI Search config
        if (!configSysId) {
            var grConfig = new GlideRecord('sys_search_context_config');
            grConfig.addQuery('search_engine', 'ai_search');
            grConfig.addNotNullQuery('search_profile');
            grConfig.setLimit(1);
            grConfig.query();

            if (grConfig.next()) {
                configSysId = grConfig.getUniqueValue();
            } else {
                response.setStatus(404);
                response.setBody({
                    success: false,
                    error: 'No AI Search configuration found. Please configure AI Search or provide a config_sys_id.'
                });
                return;
            }
        }

        // Verify config exists
        var grVerify = new GlideRecord('sys_search_context_config');
        if (!grVerify.get(configSysId)) {
            response.setStatus(404);
            response.setBody({
                success: false,
                error: 'Invalid config_sys_id: ' + configSysId
            });
            return;
        }

        // Execute AI Search
        var searchAPI = new sn_search.ScriptableSearchAPI();
        var searchResponse = searchAPI.search(
            configSysId,
            searchQuery,
            '',                    // paginationToken
            disableSpellCheck,
            [],                    // facetFilters
            [],                    // searchFilters
            {}                     // requestedFields
        );

        if (!searchResponse) {
            response.setStatus(500);
            response.setBody({
                success: false,
                error: 'AI Search returned null response'
            });
            return;
        }

        // Process results
        var results = [];
        var searchResults = searchResponse.getSearchResults();
        var correctedTerm = searchResponse.getTerm() || searchQuery;

        if (searchResults && searchResults.length > 0) {
            var limit = Math.min(searchResults.length, maxResults);

            for (var i = 0; i < limit; i++) {
                var result = searchResults[i];

                // Skip attachments
                if (result.getTable() === 'sys_attachment') {
                    continue;
                }

                results.push({
                    sys_id: result.getSysId() || '',
                    table: result.getTable() || '',
                    title: result.getTitle() || '',
                    snippet: result.getText() || '',
                    url: result.getURL() || '',
                    score: result.getScore() || 0
                });
            }
        }

        // Return successful response
        response.setStatus(200);
        response.setBody({
            success: true,
            query: searchQuery,
            corrected_query: correctedTerm,
            config_sys_id: configSysId,
            result_count: results.length,
            results: results
        });

    } catch (error) {
        gs.error('[MCP AI Search API] Error: ' + error.message);
        response.setStatus(500);
        response.setBody({
            success: false,
            error: error.message
        });
    }

})(request, response);
```

5. **Click Submit**

## Step 3: Create the List Profiles Resource

1. **In the Resources tab, click New again**

2. **Configure the Resource:**
   - **Name**: `List Profiles`
   - **HTTP method**: `GET`
   - **Relative path**: `/profiles`
   - **Description**: `List available AI Search profiles and configurations`

3. **Add the Script:**

```javascript
(function process(/*RESTAPIRequest*/ request, /*RESTAPIResponse*/ response) {

    try {
        var configs = [];

        var grConfig = new GlideRecord('sys_search_context_config');
        grConfig.addQuery('search_engine', 'ai_search');
        grConfig.addNotNullQuery('search_profile');
        grConfig.query();

        while (grConfig.next()) {
            var configSysId = grConfig.getUniqueValue();
            var profileSysId = grConfig.getValue('search_profile');
            var configName = grConfig.getValue('name') || 'Unnamed Config';

            // Get profile details
            var profileName = configName;
            var grProfile = new GlideRecord('ais_search_profile');
            if (grProfile.get(profileSysId)) {
                profileName = grProfile.getValue('label') || grProfile.getValue('name') || configName;
            }

            configs.push({
                config_sys_id: configSysId,
                config_name: configName,
                profile_sys_id: profileSysId,
                profile_name: profileName
            });
        }

        response.setStatus(200);
        response.setBody({
            success: true,
            count: configs.length,
            configs: configs
        });

    } catch (error) {
        gs.error('[MCP AI Search API] Error listing profiles: ' + error.message);
        response.setStatus(500);
        response.setBody({
            success: false,
            error: error.message
        });
    }

})(request, response);
```

4. **Click Submit**

## Step 4: Get Your API Base Path

1. **Go back to your Scripted REST API record** (`MCP AI Search API`)
2. **Note the Base API path** - it will be something like:
   ```
   /api/x_<scope>/mcp_ai_search
   ```
   For global scope, it will be:
   ```
   /api/now/mcp_ai_search
   ```

## Step 5: Test the API

### Test with REST API Explorer (Built-in)

1. **Navigate to**: **System Web Services > REST API Explorer**
2. **Select your API**: `MCP AI Search API`
3. **Select the Search resource**
4. **Set the request body**:
   ```json
   {
       "query": "how to reset password",
       "max_results": 5
   }
   ```
5. **Click Send**
6. **Verify you get results**

### Test with cURL

```bash
curl -X POST "https://demoallwf40768.service-now.com/api/now/mcp_ai_search/search" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -u "claude.desktop:z-$+88H^qXH_%^-#?op=Vsj" \
  -d '{
    "query": "password reset",
    "max_results": 5
  }'
```

## Security Considerations

### For Production Use:

1. **Enable ACL Protection**
   - Edit the Scripted REST API record
   - Set **Protection** to `Basic Auth` or create custom ACL

2. **Create a Service Account**
   - Don't use your personal credentials
   - Create a dedicated integration user with minimal required permissions

3. **Required Roles**
   The API user needs:
   - `sn_search.user` - To use AI Search API
   - `web_service_admin` - To access REST API (or custom role)

4. **Rate Limiting**
   Consider implementing rate limiting if this will be heavily used

## Troubleshooting

### Error: "sn_search.ScriptableSearchAPI is not available"
- Verify AI Search is provisioned on your instance
- Check that the user has the `sn_search` role
- Ensure you're on Washington DC or later release

### Error: "No AI Search configuration found"
- Navigate to **AI Search > AI Search Admin**
- Verify at least one AI Search profile is configured
- Check sys_search_context_config table has records with search_engine = 'ai_search'

### Error: "Invalid credentials"
- Verify username and password are correct
- Check that the user has necessary roles
- Try accessing ServiceNow UI with the same credentials

## Next Steps

Once this REST API is working:
1. Test it with the cURL command above
2. Verify you get search results back
3. Note your API base path for the MCP server configuration
4. Proceed to add the MCP tool to your server.py

---

**Ready for the next step?** Once you've confirmed the REST API is working, I'll add the AI Search tool to your MCP server!
