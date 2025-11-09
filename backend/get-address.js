require('dotenv').config();
const { Wallet } = require('ethers');
console.log("Server Address:", new Wallet(process.env.SERVER_PRIVATE_KEY).address);