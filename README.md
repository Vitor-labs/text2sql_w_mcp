# 🗣️ Text2SQL Agent

A powerful text-to-SQL agent that translates natural language queries into SQL statements and executes them on your database. Built with Google's Gemini AI, Model Context Protocol (MCP), and SQLite.

## 🚀 Features

- **Natural Language to SQL**: Convert plain English questions into SQL queries
- **Database Execution**: Automatically execute generated SQL queries
- **Schema Inspection**: Get detailed information about your database structure
- **Formatted Results**: View query results in clean, readable tables
- **Dual Interface**: Use either a web interface (Streamlit) or command-line interface
- **Error Handling**: Comprehensive error handling with helpful messages
- **Tool Integration**: Seamless integration between AI model and database tools via MCP

## 📋 Prerequisites

- Python 3.12+
- Google API Key (for Gemini)
- SQLite database

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd text2sql-agent
```

2. **Install dependencies**:

- 2.1. **Using PIP**
  ```bash
  pip install -r requirements.txt
  ```
- 2.2 **Using UV**
  ```bash
  uv sync
  ```

3. **Set up environment variables**:
Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

4. **Prepare your database**:
Make sure you have a SQLite database file named `database.db` in the project root, or the system will create an empty one for you.

## 📁 Project Structure

```
text2sql-agent/
├── src/
│   ├── client/
│   │   └── client.py          # Chat client with MCP integration
│   ├── main/
│   │   └── server.py          # MCP server with SQL tools
│   └── app.py                 # Streamlit web interface
├── run.py                     # CLI entry point
├── database.db               # SQLite database (created if not exists)
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🌐 Using the Streamlit Web Interface

### Starting the Application

Run the Streamlit app:
```bash
streamlit run src/app.py
```
or run with UV:
```bash
uv run web
```

The application will open in your default browser at `http://localhost:8501`.

### Interface Overview

- **Chat Interface**: The main area displays your conversation history
- **Input Box**: Type your questions or SQL requests at the bottom
- **Sidebar**: Contains information about available commands and a clear history button

### Example Interactions

**Getting Database Schema**:
```
You: "What tables do I have in my database?"
Assistant: [Shows formatted table with all tables and their structure]
```

**Natural Language Queries**:
```
You: "Show me all users who registered in the last 30 days"
Assistant: [Generates and executes SQL, shows results in a table]
```

**Direct SQL**:
```
You: "SELECT COUNT(*) FROM users"
Assistant: [Executes the query and shows results]
```

**Data Analysis**:
```
You: "What's the average age of users by city?"
Assistant: [Generates appropriate SQL with GROUP BY and AVG, shows results]
```

### Features

- **Auto-formatting**: Results are displayed in clean markdown tables
- **Error Messages**: Clear error messages if something goes wrong
- **History**: Full conversation history maintained during session
- **Clear History**: Button to reset the conversation
- **Processing Indicator**: Shows when the system is working on your request

## 💻 Using the CLI Interface

### Starting the CLI

Run the command-line interface:
```bash
python run.py
```

### CLI Commands

The CLI provides the same functionality as the web interface but in a terminal environment:

```bash
🤖 SQL Assistant ready! Type 'quit' to exit.

💬 Query: What tables are in my database?
🔄 Processing...

🤖 Assistant: I can see the following tables in your database:
[Table information displayed here]

💬 Query: Show me all users
🔄 Processing...

🤖 Assistant: Here are all the users:
| id | name | email | created_at |
|----|------|-------|------------|
| 1  | John | john@example.com | 2024-01-01 |
...

💬 Query: quit
👋 Goodbye!
```

### CLI Features

- **Interactive**: Type queries and get immediate responses
- **Exit Commands**: Type `quit`, `exit`, or `bye` to close
- **Keyboard Interrupt**: Press Ctrl+C to exit gracefully
- **Same Functionality**: All web interface features available in CLI

## 🛠️ Available Tools

The agent has access to the following tools:

### `query_data(sql: str)`
- Executes SQL queries on the database
- Returns formatted results
- Handles SELECT, INSERT, UPDATE, DELETE operations
- Provides row count for modification operations

### `get_schema()`
- Returns complete database schema information
- Shows tables, columns, data types, constraints
- Helps the AI understand your database structure

## 🔧 Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Your Google API key for Gemini access (required)

### Database Configuration

The system uses SQLite by default with the database file `database.db`. You can modify the database path in `src/main/server.py`:

```python
DB_PATH = Path("./your_database.db")
```

### Model Configuration

The default model is `gemini-2.0-flash`. You can change this in `src/client/client.py`:

```python
response = self.genai_client.models.generate_content(
    model="gemini-pro",  # Change model here
    contents=content_list,
    tools=tools if tools else None
)
```

## 🐛 Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not found"**:
- Make sure your `.env` file exists and contains your API key
- Verify the API key is valid and has appropriate permissions

**"Database is not accessible"**:
- Check that the database file exists and is readable
- Verify SQLite is properly installed

**"Tool execution failed"**:
- Check your SQL syntax
- Verify the table/column names exist in your database
- Look at the detailed error message for specific issues

**MCP Connection Issues**:
- Ensure the server script path is correct
- Check that all dependencies are installed
- Verify Python path is correctly set

### Logging

The application includes comprehensive logging. To see detailed logs, you can modify the logging level in the respective files:

```python
logging.basicConfig(level=logging.DEBUG)  # For more detailed logs
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and test them
4. Commit your changes: `git commit -am 'Add new feature'`
5. Push to the branch: `git push origin feature/new-feature`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google's Gemini AI for natural language processing
- Model Context Protocol (MCP) for seamless tool integration
- Streamlit for the beautiful web interface
- FastMCP for simplified MCP server implementation

---

**Happy querying!** 🎉

For questions or issues, please open an issue on the repository or contact the maintainers.