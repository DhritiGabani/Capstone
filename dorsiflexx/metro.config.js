// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

// Add .tflite extension for TensorFlow Lite model files
config.resolver.assetExts.push('tflite');

module.exports = config;
