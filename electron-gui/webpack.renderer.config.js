const path = require('path');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const commonConfig = require('./webpack.common');

module.exports = {
  ...commonConfig,
  
  // Entry points for renderer processes
  entry: {
    admin: './renderer/admin/index.tsx',
    user: './renderer/user/index.tsx',
    developer: './renderer/developer/index.tsx',
    node: './renderer/node/index.tsx',
  },
  
  // Output configuration
  output: {
    path: path.resolve(__dirname, 'dist/renderer'),
    filename: '[name]/[name].js',
    chunkFilename: '[name]/[id].chunk.js',
    clean: true,
    publicPath: './',
  },
  
  // Target for browser environment
  target: 'electron-renderer',
  
  // Renderer process specific rules
  module: {
    ...commonConfig.module,
    rules: [
      ...commonConfig.module.rules,
      // React JSX handling
      {
        test: /\.(ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader',
          options: {
            transpileOnly: true,
            compilerOptions: {
              jsx: 'react-jsx',
            },
          },
        },
      },
      // SCSS/SASS files
      {
        test: /\.(scss|sass)$/,
        use: [
          'style-loader',
          'css-loader',
          'sass-loader',
        ],
      },
    ],
  },
  
  // Plugins for renderer process
  plugins: [
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
      'process.env.ELECTRON_ENV': JSON.stringify('renderer'),
    }),
    
    // HTML templates for each GUI
    new HtmlWebpackPlugin({
      template: './renderer/admin/admin.html',
      filename: 'admin/admin.html',
      chunks: ['admin', 'common', 'vendors'],
      inject: 'body',
    }),
    
    new HtmlWebpackPlugin({
      template: './renderer/user/user.html',
      filename: 'user/user.html',
      chunks: ['user', 'common', 'vendors'],
      inject: 'body',
    }),
    
    new HtmlWebpackPlugin({
      template: './renderer/developer/developer.html',
      filename: 'developer/developer.html',
      chunks: ['developer', 'common', 'vendors'],
      inject: 'body',
    }),
    
    new HtmlWebpackPlugin({
      template: './renderer/node/node.html',
      filename: 'node/node.html',
      chunks: ['node', 'common', 'vendors'],
      inject: 'body',
    }),
    
    // Environment variables
    new webpack.EnvironmentPlugin({
      NODE_ENV: 'development',
      ELECTRON_ENV: 'renderer',
    }),
  ],
  
  // Renderer process specific optimizations
  optimization: {
    ...commonConfig.optimization,
    minimize: process.env.NODE_ENV === 'production',
    usedExports: true,
    sideEffects: false,
  },
  
  // Development server configuration
  devServer: {
    port: 3000,
    hot: true,
    liveReload: true,
    historyApiFallback: {
      rewrites: [
        { from: /^\/admin/, to: '/admin/admin.html' },
        { from: /^\/user/, to: '/user/user.html' },
        { from: /^\/developer/, to: '/developer/developer.html' },
        { from: /^\/node/, to: '/node/node.html' },
      ],
    },
    static: {
      directory: path.join(__dirname, 'assets'),
      publicPath: '/assets',
    },
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization',
    },
    compress: true,
    client: {
      logging: 'info',
      overlay: {
        errors: true,
        warnings: false,
      },
    },
  },
  
  // Resolve configuration for renderer process
  resolve: {
    ...commonConfig.resolve,
    fallback: {
      "fs": false,
      "path": false,
      "os": false,
      "crypto": false,
      "stream": false,
      "util": false,
      "buffer": false,
      "events": false,
      "assert": false,
      "http": false,
      "https": false,
      "url": false,
      "querystring": false,
    },
  },
  
  // Mode
  mode: process.env.NODE_ENV === 'production' ? 'production' : 'development',
};
