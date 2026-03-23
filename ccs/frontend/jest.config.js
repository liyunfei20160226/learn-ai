/** @type {import('jest').Config} */
const config = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  transform: {
    "^.+\\.(ts|tsx)$": "babel-jest",
  },
  testMatch: ["**/__tests__/**/*.(ts|tsx)", "**/*.test.(ts|tsx)"],
  collectCoverageFrom: ["src/**/*.{ts,tsx}", "!src/**/*.d.ts"],
  coverageReporters: ["text", "lcov", "html"],
  coverageDirectory: "coverage",
};

module.exports = config;
