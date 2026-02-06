import { network } from "hardhat";

async function main() {
  const { ethers } = await network.connect();
  // Parse target address from CLI args or env
  const argv = process.argv.slice(2);
  const argAddressEq = argv.find((a) => a.startsWith("--address="))?.split("=")[1];
  const argAddrShortEq = argv.find((a) => a.startsWith("--addr="))?.split("=")[1];
  const positional = argv.find((a) => a.startsWith("0x") && a.length >= 42);
  const envAddress = process.env.ADDRESS ?? process.env.TARGET_ADDRESS;

  let target = argAddressEq ?? argAddrShortEq ?? positional ?? envAddress;
  if (!target || !ethers.isAddress(target)) {
    const [deployer] = await ethers.getSigners();
    target = deployer.address;
  }

  const balance = await ethers.provider.getBalance(target);

  console.log(`\nAddress being used: ${target}`);
  console.log(`Balance of this address: ${ethers.formatEther(balance)} ETH\n`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
