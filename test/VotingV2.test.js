import { expect } from "chai";
import { network } from "hardhat";

// Hardhat 3 ESM pattern
const { ethers } = await network.connect();

describe.skip("VotingV2 contract (Kiosk model) — skipped (legacy test)", function () {
  let admin, signer1, signer2, attacker;
  let VotingV2Factory, votingV2;

  beforeEach(async function () {
    [admin, signer1, signer2, attacker] = await ethers.getSigners();
    VotingV2Factory = await ethers.getContractFactory("VotingV2", admin);
    votingV2 = await VotingV2Factory.deploy();
    await votingV2.waitForDeployment();
  });

  describe("Deployment", function () {
    it("sets deployer as admin and election active", async function () {
      expect(await votingV2.admin()).to.equal(admin.address);
      expect(await votingV2.isElectionActive()).to.equal(true);
    });
  });

  describe("Signer authorization", function () {
    it("admin can authorize signer", async function () {
      await expect(votingV2.connect(admin).authorizeSigner(signer1.address))
        .to.emit(votingV2, "SignerAuthorized")
        .withArgs(signer1.address);
      expect(await votingV2.authorizedSigners(signer1.address)).to.equal(true);
    });

    it("non-admin cannot authorize signer", async function () {
      await expect(
        votingV2.connect(attacker).authorizeSigner(signer1.address)
      ).to.be.revertedWith("Only admin can perform this action.");
    });
  });

  describe("Candidate management & voting flow", function () {
    beforeEach(async function () {
      // authorize a backend signer
      await votingV2.connect(admin).authorizeSigner(signer1.address);
      // add candidates
      await votingV2.connect(admin).addCandidate("Alice");
      await votingV2.connect(admin).addCandidate("Bob");
    });

    it("authorized signer can cast a vote for a voterId", async function () {
      await expect(
        votingV2.connect(signer1).vote(1, "voter-uuid-123")
      ).to.emit(votingV2, "VoteCast")
       .withArgs(signer1.address, 1, "voter-uuid-123");

      const candidate = await votingV2.getCandidate(1);
      expect(candidate[2]).to.equal(1); // voteCount
      expect(await votingV2.totalVotes()).to.equal(1);
      expect(await votingV2.hasVoted("voter-uuid-123")).to.equal(true);
    });

    it("non-authorized address cannot cast vote", async function () {
      await expect(
        votingV2.connect(attacker).vote(1, "voter-uuid-123")
      ).to.be.revertedWith("Only authorized signer can perform this action.");
    });

    it("same voterId cannot vote twice (double-vote prevention)", async function () {
      await votingV2.connect(signer1).vote(1, "voter-uuid-123");
      await expect(
        votingV2.connect(signer1).vote(2, "voter-uuid-123")
      ).to.be.revertedWith("Voter ID already used.");
    });

    it("rejects invalid candidate id", async function () {
      await expect(
        votingV2.connect(signer1).vote(0, "voter-uuid-999")
      ).to.be.revertedWith("Invalid candidate ID.");
      await expect(
        votingV2.connect(signer1).vote(999, "voter-uuid-999")
      ).to.be.revertedWith("Invalid candidate ID.");
    });

    it("rejects empty voterId", async function () {
      await expect(
        votingV2.connect(signer1).vote(1, "")
      ).to.be.revertedWith("voterId cannot be empty.");
    });
  });

  describe("Election lifecycle", function () {
    beforeEach(async function () {
      await votingV2.connect(admin).addCandidate("Alice");
      await votingV2.connect(admin).authorizeSigner(signer1.address);
    });

    it("admin can end election and winner details available", async function () {
      // Cast one vote so Alice wins
      await votingV2.connect(signer1).vote(1, "voter-uuid-abc");
      await expect(votingV2.connect(admin).endElection())
        .to.emit(votingV2, "ElectionEnded")
        .withArgs(1, "Alice", 1);
      expect(await votingV2.isElectionActive()).to.equal(false);
      const winnerId = await votingV2.getWinner();
      expect(winnerId).to.equal(1);
    });

    it("cannot end election with no candidates", async function () {
      // deploy fresh to remove candidate
      VotingV2Factory = await ethers.getContractFactory("VotingV2", admin);
      votingV2 = await VotingV2Factory.deploy();
      await votingV2.waitForDeployment();
      await expect(votingV2.connect(admin).endElection()).to.be.revertedWith(
        "Cannot end election with no candidates."
      );
    });

    it("can restart election after ending", async function () {
      await votingV2.connect(admin).endElection();
      expect(await votingV2.isElectionActive()).to.equal(false);
      await expect(votingV2.connect(admin).startElection())
        .to.emit(votingV2, "ElectionStarted");
      expect(await votingV2.isElectionActive()).to.equal(true);
    });
  });
});
