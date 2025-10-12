import "dotenv/config";
import type { HardhatUserConfig } from "hardhat/config";
import "./tasks/check-balance";
import hardhatToolboxMochaEthersPlugin from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { configVariable } from "hardhat/config";

// Prefer values from .env (loaded above), and fall back to Hardhat keystore config variables
const sepoliaUrl = process.env.SEPOLIA_RPC_URL ?? configVariable("SEPOLIA_RPC_URL");
const sepoliaPkFromEnv = process.env.SEPOLIA_PRIVATE_KEY;
const sepoliaPk = sepoliaPkFromEnv
  ? (sepoliaPkFromEnv.startsWith("0x") ? sepoliaPkFromEnv : `0x${sepoliaPkFromEnv}`)
  : configVariable("SEPOLIA_PRIVATE_KEY");
const sepoliaAccounts = [sepoliaPk];

const config: HardhatUserConfig = {
  plugins: [hardhatToolboxMochaEthersPlugin],
  solidity: {
    profiles: {
      default: {
        version: "0.8.28",
      },
      production: {
        version: "0.8.28",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
    },
  },
  networks: {
    hardhatMainnet: {
      type: "edr-simulated",
      chainType: "l1",
    },
    hardhatOp: {
      type: "edr-simulated",
      chainType: "op",
    },
    sepolia: {
      type: "http",
      chainType: "l1",
      url: sepoliaUrl,
      accounts: sepoliaAccounts,
    },
  },
};

export default config;
