#!/usr/bin/env node

/**
 * Lucid API Documentation Generator
 * Generates comprehensive API documentation for all service clusters
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const chalk = require('chalk');
const ora = require('ora');

// Configuration
const config = {
  projectRoot: path.join(__dirname, '../..'),
  docsDir: path.join(__dirname, '.'),
  openapiDir: path.join(__dirname, 'openapi'),
  generatedDir: path.join(__dirname, 'generated'),
  swaggerUiDir: path.join(__dirname, 'swagger-ui'),
  redocDir: path.join(__dirname, 'redoc'),
  sdksDir: path.join(__dirname, 'sdks')
};

// Services configuration
const services = [
  {
    name: 'api-gateway',
    title: 'API Gateway',
    description: 'Primary entry point for all API requests',
    port: 8080
  },
  {
    name: 'blockchain-core',
    title: 'Blockchain Core',
    description: 'Core blockchain operations and consensus',
    port: 8081
  },
  {
    name: 'session-management',
    title: 'Session Management',
    description: 'User session and data storage management',
    port: 8082
  },
  {
    name: 'rdp-services',
    title: 'RDP Services',
    description: 'Remote desktop protocol services',
    port: 8083
  },
  {
    name: 'node-management',
    title: 'Node Management',
    description: 'Worker node coordination and management',
    port: 8084
  },
  {
    name: 'admin-interface',
    title: 'Admin Interface',
    description: 'System administration and monitoring',
    port: 8085
  },
  {
    name: 'tron-payment',
    title: 'TRON Payment',
    description: 'TRON blockchain payment processing',
    port: 8086
  },
  {
    name: 'auth-service',
    title: 'Auth Service',
    description: 'Authentication and authorization',
    port: 8087
  }
];

// Utility functions
const log = {
  info: (msg) => console.log(chalk.blue(`[INFO] ${msg}`)),
  success: (msg) => console.log(chalk.green(`[SUCCESS] ${msg}`)),
  warning: (msg) => console.log(chalk.yellow(`[WARNING] ${msg}`)),
  error: (msg) => console.log(chalk.red(`[ERROR] ${msg}`))
};

// Check if file exists
function fileExists(filePath) {
  try {
    return fs.statSync(filePath).isFile();
  } catch (err) {
    return false;
  }
}

// Check if directory exists
function dirExists(dirPath) {
  try {
    return fs.statSync(dirPath).isDirectory();
  } catch (err) {
    return false;
  }
}

// Create directory if it doesn't exist
function ensureDir(dirPath) {
  if (!dirExists(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    log.info(`Created directory: ${dirPath}`);
  }
}

// Validate OpenAPI specifications
function validateSpecs() {
  log.info('Validating OpenAPI specifications...');
  
  const invalidSpecs = [];
  
  services.forEach(service => {
    const specPath = path.join(config.openapiDir, `${service.name}.yaml`);
    
    if (fileExists(specPath)) {
      try {
        // Basic YAML validation
        const content = fs.readFileSync(specPath, 'utf8');
        const yaml = require('js-yaml');
        yaml.load(content);
        log.success(`${service.name}.yaml is valid`);
      } catch (err) {
        log.error(`${service.name}.yaml is invalid: ${err.message}`);
        invalidSpecs.push(service.name);
      }
    } else {
      log.warning(`${service.name}.yaml not found`);
    }
  });
  
  if (invalidSpecs.length > 0) {
    log.error(`Invalid specifications: ${invalidSpecs.join(', ')}`);
    return false;
  }
  
  return true;
}

// Generate Swagger UI for each service
function generateSwaggerUI() {
  log.info('Generating Swagger UI...');
  
  ensureDir(config.swaggerUiDir);
  
  services.forEach(service => {
    const serviceDir = path.join(config.swaggerUiDir, service.name);
    ensureDir(serviceDir);
    
    // Create index.html for service
    const indexHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid ${service.title} API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #1f2937;
        }
        .swagger-ui .topbar .download-url-wrapper {
            display: none;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '../openapi/${service.name}.yaml',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                onComplete: function() {
                    console.log('${service.title} API documentation loaded');
                }
            });
        };
    </script>
</body>
</html>`;
    
    fs.writeFileSync(path.join(serviceDir, 'index.html'), indexHtml);
    log.success(`Swagger UI generated for ${service.title}`);
  });
}

// Generate ReDoc documentation
function generateReDoc() {
  log.info('Generating ReDoc documentation...');
  
  ensureDir(config.redocDir);
  
  services.forEach(service => {
    const specPath = path.join(config.openapiDir, `${service.name}.yaml`);
    const outputPath = path.join(config.redocDir, `${service.name}.html`);
    
    if (fileExists(specPath)) {
      try {
        // Generate ReDoc HTML
        const redocHtml = `<!DOCTYPE html>
<html>
<head>
    <title>Lucid ${service.title} API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <redoc spec-url="../openapi/${service.name}.yaml"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>`;
        
        fs.writeFileSync(outputPath, redocHtml);
        log.success(`ReDoc generated for ${service.title}`);
      } catch (err) {
        log.error(`Failed to generate ReDoc for ${service.title}: ${err.message}`);
      }
    }
  });
}

// Generate main index page
function generateIndex() {
  log.info('Generating main index page...');
  
  const indexHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid API Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .service-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .service-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .service-card h3 {
            margin: 0 0 10px 0;
            color: #2d3748;
            font-size: 1.3em;
        }
        .service-card p {
            margin: 0 0 15px 0;
            color: #718096;
            font-size: 0.9em;
        }
        .service-links {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .service-links a {
            display: inline-block;
            padding: 8px 16px;
            background: #4299e1;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background 0.2s;
        }
        .service-links a:hover {
            background: #3182ce;
        }
        .service-links a.swagger {
            background: #85ea2d;
        }
        .service-links a.swagger:hover {
            background: #68d391;
        }
        .service-links a.redoc {
            background: #ed8936;
        }
        .service-links a.redoc:hover {
            background: #dd6b20;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: #2d3748;
            color: white;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Lucid API Documentation</h1>
        <p>Comprehensive API documentation for the Lucid blockchain system</p>
    </div>
    
    <div class="services-grid">
        ${services.map(service => `
        <div class="service-card">
            <h3>${service.title}</h3>
            <p>${service.description}</p>
            <div class="service-links">
                <a href="swagger-ui/${service.name}/" class="swagger">Swagger UI</a>
                <a href="redoc/${service.name}.html" class="redoc">ReDoc</a>
                <a href="openapi/${service.name}.yaml">OpenAPI Spec</a>
            </div>
        </div>
        `).join('')}
    </div>
    
    <div class="footer">
        <p>Lucid Blockchain System API Documentation</p>
        <p>Generated on ${new Date().toISOString()}</p>
    </div>
</body>
</html>`;
  
  fs.writeFileSync(path.join(config.docsDir, 'index.html'), indexHtml);
  log.success('Main index page generated');
}

// Main execution function
function main() {
  log.info('Starting Lucid API documentation generation...');
  
  try {
    // Create necessary directories
    ensureDir(config.generatedDir);
    ensureDir(config.swaggerUiDir);
    ensureDir(config.redocDir);
    ensureDir(config.sdksDir);
    
    // Validate specifications
    if (!validateSpecs()) {
      log.error('Validation failed. Exiting.');
      process.exit(1);
    }
    
    // Generate documentation
    generateSwaggerUI();
    generateReDoc();
    generateIndex();
    
    log.success('API documentation generation completed successfully!');
    log.info(`Documentation available at: ${config.docsDir}`);
    log.info(`Swagger UI available at: ${config.swaggerUiDir}`);
    log.info(`ReDoc available at: ${config.redocDir}`);
    
  } catch (err) {
    log.error(`Generation failed: ${err.message}`);
    process.exit(1);
  }
}

// Handle command line arguments
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Lucid API Documentation Generator

Usage: node generate-docs.js [OPTIONS]

Options:
  --help, -h     Show this help message
  --validate     Only validate OpenAPI specifications
  --swagger      Only generate Swagger UI
  --redoc        Only generate ReDoc
  --index        Only generate index page

Examples:
  node generate-docs.js                    # Generate all documentation
  node generate-docs.js --validate         # Only validate specs
  node generate-docs.js --swagger          # Only generate Swagger UI
    `);
    process.exit(0);
  }
  
  if (args.includes('--validate')) {
    validateSpecs();
  } else if (args.includes('--swagger')) {
    generateSwaggerUI();
  } else if (args.includes('--redoc')) {
    generateReDoc();
  } else if (args.includes('--index')) {
    generateIndex();
  } else {
    main();
  }
}

module.exports = {
  validateSpecs,
  generateSwaggerUI,
  generateReDoc,
  generateIndex,
  main
};
