// Metro config for a monorepo: watch the workspace root so Metro can transpile
// the shared TypeScript package, and resolve @lakasmarket/shared to its source.
const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "..");

const config = getDefaultConfig(projectRoot);

config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, "node_modules"),
  path.resolve(workspaceRoot, "node_modules"),
];
config.resolver.extraNodeModules = {
  "@lakasmarket/shared": path.resolve(workspaceRoot, "packages/shared/src"),
};

module.exports = config;
