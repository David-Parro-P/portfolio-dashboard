# IBKR Statement Analytics 📊 📈

A comprehensive platform for processing and visualizing Interactive Brokers statements with focused tracking of options credits and forex balances.

## Overview 🔍

IBKR Statement Analytics automates the collection, processing, and visualization of Interactive Brokers statements to provide better insight into your portfolio, with special attention to tracking sold options credit alongside forex balances - metrics that are typically difficult to monitor simultaneously in standard brokerage interfaces.

The system follows a streamlined data pipeline:
1. **Collection** : N8n workflows fetch custom statements from Interactive Brokers
2. **Processing** : Custom Python service parses and transforms statement data
3. **Storage** : Processed data is stored in structured database tables
4. **Visualization** : Metabase provides customizable dashboards and analytics

## Architecture 🏗️

The platform consists of four main services, orchestrated with Docker Compose:

### 1. N8n (Automation) 🤖
- Handles statement retrieval from IBKR via email integration
- Schedules regular data processing workflows
- Manages the initial data pipeline stage

### 2. Processor (Data Transformation) 🔄
- Flask-based Python service that processes raw IBKR statement data
- Parses complex statement formats including MTM summaries and trade data
- Separates and transforms data for stocks, options, and forex into structured tables
- Calculates important portfolio metrics including options credit positions

### 3. Database 🗄️
- SQLite database stores structured financial data
- Maintains historical records for trend analysis
- Organized schema optimized for financial reporting

### 4. Metabase (Visualization) 📈
- Rich interactive dashboards for portfolio analysis
- Custom queries and reports
- Tracking of critical metrics like:
  - Options credit positions over time
  - Forex balances and currency exposure
  - Stock positions and performance

### 5. Nginx (Web Server) 🌐
- Provides secure access to the platform components
- Handles SSL termination and routing

## Key Features ✨

- **Options Credit Tracking** : Maintain visibility on outstanding options credit separate from forex balances
- **Consolidated View** : See your entire portfolio across asset classes in one dashboard
- **Historical Analysis** : Track changes in positions and balances over time
- **Automated Processing** : Set-and-forget data pipeline with minimal maintenance
- **Secure Access** : Protected endpoints for all services

## Deployment 🚀

The entire platform is containerized using Docker and can be deployed on any system that supports Docker Compose.

```yaml
# docker-compose.yml included in the repository
```

## Environment Variables 🔧

The following environment variables are required:

```
N8N_USER=your_username
N8N_PASSWORD=your_password
N8N_ENCRYPTION_KEY=your_encryption_key
N8N_HOST=your_domain
DOCKER_USERNAME=your_docker_username
IMAGE_NAME=statement-analytics
METABASE_ADMIN_EMAIL=admin@example.com
METABASE_ADMIN_PASSWORD=your_metabase_password
```

## Getting Started 🚦

1. Clone the repository
2. Configure environment variables
3. Run `docker-compose up -d`
4. Access Metabase at `http://your-server:3000`
5. Set up N8n workflows to fetch IBKR statements

## Use Cases 💼

- **Options Traders** : Track credit received from selling options separately from cash balances
- **Multi-Currency Investors** : Monitor forex exposure alongside investment positions
- **Portfolio Managers** : Get comprehensive views of diverse portfolios
- **Financial Analysts** : Generate insights from historical trading data

## License ⚖️

MIT License

## Contributions 🤝

Contributions welcome! Please submit a pull request or open an issue to discuss potential improvements