// main/ipc/api-handler.ts - API proxy IPC handlers
// Based on the electron-multi-gui-development.plan.md specifications

import { ipcMain } from 'electron';
import { WindowManager } from '../window-manager';
import { 
  RENDERER_TO_MAIN_CHANNELS, 
  MAIN_TO_RENDERER_CHANNELS,
  APIRequestMessage,
  APIResponseMessage,
  APIErrorMessage
} from '../../shared/ipc-channels';

export function setupApiHandlers(windowManager: WindowManager): void {
  console.log('Setting up API proxy IPC handlers...');

  // Generic API request handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_REQUEST, async (event, request: APIRequestMessage) => {
    try {
      const { method, url, data, headers = {}, timeout = 30000 } = request;
      
      console.log(`API ${method} request to: ${url}`);
      
      // Make the API request
      const response = await makeApiRequest(method, url, data, headers, timeout);
      
      // Send response back to renderer
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: response.data,
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API request error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown API error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  // GET request handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_GET, async (event, { url, headers = {}, timeout = 30000 }) => {
    try {
      console.log(`API GET request to: ${url}`);
      
      const response = await makeApiRequest('GET', url, undefined, headers, timeout);
      
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: response.data,
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API GET error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown GET error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  // POST request handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_POST, async (event, { url, data, headers = {}, timeout = 30000 }) => {
    try {
      console.log(`API POST request to: ${url}`);
      
      const response = await makeApiRequest('POST', url, data, headers, timeout);
      
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: response.data,
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API POST error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown POST error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  // PUT request handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_PUT, async (event, { url, data, headers = {}, timeout = 30000 }) => {
    try {
      console.log(`API PUT request to: ${url}`);
      
      const response = await makeApiRequest('PUT', url, data, headers, timeout);
      
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: response.data,
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API PUT error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown PUT error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  // DELETE request handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_DELETE, async (event, { url, headers = {}, timeout = 30000 }) => {
    try {
      console.log(`API DELETE request to: ${url}`);
      
      const response = await makeApiRequest('DELETE', url, undefined, headers, timeout);
      
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: response.data,
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API DELETE error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown DELETE error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  // File upload handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_UPLOAD, async (event, { url, filePath, formData, headers = {}, timeout = 60000 }) => {
    try {
      console.log(`API file upload to: ${url}`);
      
      const response = await makeFileUploadRequest(url, filePath, formData, headers, timeout);
      
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: response.data,
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API upload error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown upload error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  // File download handler
  ipcMain.handle(RENDERER_TO_MAIN_CHANNELS.API_DOWNLOAD, async (event, { url, savePath, headers = {}, timeout = 60000 }) => {
    try {
      console.log(`API file download from: ${url}`);
      
      const response = await makeFileDownloadRequest(url, savePath, headers, timeout);
      
      const responseMessage: APIResponseMessage = {
        requestId: generateRequestId(),
        data: { savedPath: response.savedPath, fileSize: response.fileSize },
        status: response.status,
        headers: response.headers
      };
      
      return responseMessage;
    } catch (error) {
      console.error('API download error:', error);
      
      const errorMessage: APIErrorMessage = {
        requestId: generateRequestId(),
        error: error instanceof Error ? error.message : 'Unknown download error',
        status: 500,
        details: error
      };
      
      return errorMessage;
    }
  });

  console.log('API proxy IPC handlers setup complete');
}

// Helper function to make API requests through Tor
async function makeApiRequest(
  method: string, 
  url: string, 
  data?: any, 
  headers: Record<string, string> = {}, 
  timeout: number = 30000
): Promise<{ data: any; status: number; headers: Record<string, string> }> {
  try {
    // Get Tor proxy configuration
    const proxyConfig = await getTorProxyConfig();
    
    // Prepare request options
    const requestOptions: any = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Lucid-Electron-GUI/1.0.0',
        ...headers
      },
      timeout
    };

    // Add request body for non-GET requests
    if (data && method !== 'GET') {
      requestOptions.body = typeof data === 'string' ? data : JSON.stringify(data);
    }

    // Add proxy configuration if available
    if (proxyConfig) {
      requestOptions.agent = new (require('https-proxy-agent'))(`socks5://${proxyConfig.host}:${proxyConfig.port}`);
    }

    // Make the request
    const response = await fetch(url, requestOptions);
    
    // Parse response
    let responseData;
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }

    // Convert headers to plain object
    const responseHeaders: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });

    return {
      data: responseData,
      status: response.status,
      headers: responseHeaders
    };
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// Helper function to handle file uploads
async function makeFileUploadRequest(
  url: string,
  filePath: string,
  formData: Record<string, any>,
  headers: Record<string, string> = {},
  timeout: number = 60000
): Promise<{ data: any; status: number; headers: Record<string, string> }> {
  try {
    const FormData = require('form-data');
    const fs = require('fs');
    
    // Get Tor proxy configuration
    const proxyConfig = await getTorProxyConfig();
    
    // Create form data
    const form = new FormData();
    
    // Add file to form data
    form.append('file', fs.createReadStream(filePath));
    
    // Add additional form fields
    Object.entries(formData).forEach(([key, value]) => {
      form.append(key, value);
    });

    // Prepare request options
    const requestOptions: any = {
      method: 'POST',
      headers: {
        'User-Agent': 'Lucid-Electron-GUI/1.0.0',
        ...form.getHeaders(),
        ...headers
      },
      timeout,
      body: form
    };

    // Add proxy configuration if available
    if (proxyConfig) {
      requestOptions.agent = new (require('https-proxy-agent'))(`socks5://${proxyConfig.host}:${proxyConfig.port}`);
    }

    // Make the request
    const response = await fetch(url, requestOptions);
    const responseData = await response.json();

    // Convert headers to plain object
    const responseHeaders: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });

    return {
      data: responseData,
      status: response.status,
      headers: responseHeaders
    };
  } catch (error) {
    console.error('File upload failed:', error);
    throw error;
  }
}

// Helper function to handle file downloads
async function makeFileDownloadRequest(
  url: string,
  savePath: string,
  headers: Record<string, string> = {},
  timeout: number = 60000
): Promise<{ savedPath: string; fileSize: number; status: number; headers: Record<string, string> }> {
  try {
    const fs = require('fs');
    const path = require('path');
    
    // Get Tor proxy configuration
    const proxyConfig = await getTorProxyConfig();
    
    // Prepare request options
    const requestOptions: any = {
      method: 'GET',
      headers: {
        'User-Agent': 'Lucid-Electron-GUI/1.0.0',
        ...headers
      },
      timeout
    };

    // Add proxy configuration if available
    if (proxyConfig) {
      requestOptions.agent = new (require('https-proxy-agent'))(`socks5://${proxyConfig.host}:${proxyConfig.port}`);
    }

    // Make the request
    const response = await fetch(url, requestOptions);
    
    if (!response.ok) {
      throw new Error(`Download failed with status: ${response.status}`);
    }

    // Get file size from content-length header
    const contentLength = response.headers.get('content-length');
    const fileSize = contentLength ? parseInt(contentLength, 10) : 0;

    // Create directory if it doesn't exist
    const dir = path.dirname(savePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // Download and save file
    const buffer = await response.arrayBuffer();
    fs.writeFileSync(savePath, Buffer.from(buffer));

    // Convert headers to plain object
    const responseHeaders: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });

    return {
      savedPath,
      fileSize,
      status: response.status,
      headers: responseHeaders
    };
  } catch (error) {
    console.error('File download failed:', error);
    throw error;
  }
}

// Helper function to get Tor proxy configuration
async function getTorProxyConfig(): Promise<any> {
  try {
    // This would integrate with the TorManager to get current proxy settings
    // For now, return a default SOCKS5 proxy configuration
    return {
      protocol: 'socks5',
      host: '127.0.0.1',
      port: 9050
    };
  } catch (error) {
    console.error('Failed to get Tor proxy config:', error);
    return null;
  }
}

// Helper function to generate unique request IDs
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
