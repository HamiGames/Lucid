const path = require('path');
const webpack = require('webpack');
const commonConfig = require('./webpack.common');

module.exports = {
  ...commonConfig,
  
  // Entry point for main process
  entry: {
    main: './main/index.ts',
  },
  
  // Output configuration
  output: {
    path: path.resolve(__dirname, 'dist/main'),
    filename: '[name].js',
    libraryTarget: 'commonjs2',
    clean: true,
  },
  
  // Target for Node.js environment
  target: 'electron-main',
  
  // Node.js modules that should be externalized
  externals: {
    'electron': 'commonjs electron',
    'dockerode': 'commonjs dockerode',
    'socks-proxy-agent': 'commonjs socks-proxy-agent',
  },
  
  // Main process specific rules
  module: {
    ...commonConfig.module,
    rules: [
      ...commonConfig.module.rules,
      // Additional rules for main process
      {
        test: /\.node$/,
        loader: 'node-loader',
      },
    ],
  },
  
  // Plugins for main process
  plugins: [
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
      'process.env.ELECTRON_ENV': JSON.stringify('main'),
    }),
    
    // Ignore native modules warnings
    new webpack.IgnorePlugin({
      resourceRegExp: /^(canvas|sqlite3|@mapbox\/node-pre-gyp)$/,
    }),
  ],
  
  // Main process specific optimizations
  optimization: {
    ...commonConfig.optimization,
    minimize: process.env.NODE_ENV === 'production',
  },
  
  // Resolve configuration for main process
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
  
  // Watch options for development
  watchOptions: {
    ignored: /node_modules/,
    poll: 1000,
    aggregateTimeout: 300,
  },
  
  // Mode
  mode: process.env.NODE_ENV === 'production' ? 'production' : 'development',
};
