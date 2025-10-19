const path = require('path');

module.exports = {
  // Common webpack configuration
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    alias: {
      '@shared': path.resolve(__dirname, 'shared'),
      '@main': path.resolve(__dirname, 'main'),
      '@renderer': path.resolve(__dirname, 'renderer'),
      '@assets': path.resolve(__dirname, 'assets'),
      '@configs': path.resolve(__dirname, 'configs'),
    },
  },
  
  module: {
    rules: [
      // TypeScript/JavaScript files
      {
        test: /\.(ts|tsx|js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader',
          options: {
            transpileOnly: true,
          },
        },
      },
      
      // CSS files
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
      
      // Static assets
      {
        test: /\.(png|jpe?g|gif|svg|ico)$/,
        type: 'asset/resource',
        generator: {
          filename: 'assets/images/[name][ext]',
        },
      },
      
      // Fonts
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/,
        type: 'asset/resource',
        generator: {
          filename: 'assets/fonts/[name][ext]',
        },
      },
    ],
  },
  
  // Common plugins and optimizations
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
        common: {
          name: 'common',
          minChunks: 2,
          chunks: 'all',
          enforce: true,
        },
      },
    },
  },
  
  // Performance hints
  performance: {
    hints: process.env.NODE_ENV === 'production' ? 'warning' : false,
    maxEntrypointSize: 512000,
    maxAssetSize: 512000,
  },
  
  // Source maps
  devtool: process.env.NODE_ENV === 'production' ? 'source-map' : 'eval-source-map',
  
  // Stats
  stats: {
    colors: true,
    modules: false,
    children: false,
    chunks: false,
    chunkModules: false,
  },
};
