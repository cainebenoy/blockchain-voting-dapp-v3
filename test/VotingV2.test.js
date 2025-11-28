import { expect } from "chai";
import { network } from "hardhat";

// Hardhat 3 ESM pattern
const { ethers } = await network.connect();

describe("VotingV2 contract (Kiosk model)", function () {
  let admin, signer1, attacker;
  let VotingV2Factory, votingV2;

  beforeEach(async function () {
    [admin, signer1, , attacker] = await ethers.getSigners();
    VotingV2Factory = await ethers.getContractFactory("VotingV2", admin);
    votingV2 = await VotingV2Factory.deploy();
    await votingV2.waitForDeployment();
  });

  describe("Deployment", function () {
    it("sets deployer as admin and election inactive initially", async function () {
      expect(await votingV2.admin()).to.equal(admin.address);
      expect(await votingV2.electionActive()).to.equal(false);
    });
  });

  describe("Signer authorization", function () {
    it("admin can set official signer", async function () {
      await votingV2.connect(admin).setOfficialSigner(signer1.address);
      expect(await votingV2.officialSigner()).to.equal(signer1.address);
    });

    it("non-admin cannot set official signer", async function () {
      await expect(
        votingV2.connect(attacker).setOfficialSigner(signer1.address)
      ).to.be.revertedWith("Only admin can do this");
    });
  });

  describe("Candidate management & voting flow", function () {
    beforeEach(async function () {
      // Set official signer
      await votingV2.connect(admin).setOfficialSigner(signer1.address);
      // Add candidates
      await votingV2.connect(admin).addCandidate("Alice");
      await votingV2.connect(admin).addCandidate("Bob");
      // Start election
      await votingV2.connect(admin).startElection();
    });

    it("authorized signer can cast a vote for a voterId", async function () {
      await expect(
        votingV2.connect(signer1).vote(1, "voter-uuid-123")
      ).to.emit(votingV2, "VoteCast")
       .withArgs("voter-uuid-123", 1);

      const candidate = await votingV2.candidates(1);
      expect(candidate[2]).to.equal(1); // voteCount
      expect(await votingV2.totalVotes()).to.equal(1);
      expect(await votingV2.hasVoted("voter-uuid-123")).to.equal(true);
    });

    it("non-authorized address cannot cast vote", async function () {
      await expect(
        votingV2.connect(attacker).vote(1, "voter-uuid-123")
      ).to.be.revertedWith("Not authorized kiosk signer");
    });

    it("same voterId cannot vote twice (double-vote prevention)", async function () {
      await votingV2.connect(signer1).vote(1, "voter-uuid-123");
      await expect(
        votingV2.connect(signer1).vote(2, "voter-uuid-123")
      ).to.be.revertedWith("This voter ID has already voted.");
    });

    it("rejects invalid candidate id", async function () {
      await expect(
        votingV2.connect(signer1).vote(0, "voter-uuid-999")
      ).to.be.revertedWith("Invalid candidate.");
      await expect(
        votingV2.connect(signer1).vote(999, "voter-uuid-999")
      ).to.be.revertedWith("Invalid candidate.");
    });

    it("allows empty voterId (edge case - should be handled by backend)", async function () {
      // The contract doesn't validate empty strings, backend should prevent this
      await votingV2.connect(signer1).vote(1, "");
      expect(await votingV2.hasVoted("")).to.equal(true);
    });
  });

  describe("Election lifecycle", function () {
    beforeEach(async function () {
      await votingV2.connect(admin).addCandidate("Alice");
      await votingV2.connect(admin).setOfficialSigner(signer1.address);
      await votingV2.connect(admin).startElection();
    });

    it("admin can end election", async function () {
      // Cast one vote first
      await votingV2.connect(signer1).vote(1, "voter-uuid-abc");
      await expect(votingV2.connect(admin).endElection())
        .to.emit(votingV2, "ElectionEnded")
        .withArgs(1);
      expect(await votingV2.electionActive()).to.equal(false);
    });

    it("cannot start election with no candidates", async function () {
      // Deploy fresh contract with no candidates
      VotingV2Factory = await ethers.getContractFactory("VotingV2", admin);
      votingV2 = await VotingV2Factory.deploy();
      await votingV2.waitForDeployment();
      await expect(votingV2.connect(admin).startElection()).to.be.revertedWith(
        "Must have at least one candidate"
      );
    });

    it("cannot vote when election is inactive", async function () {
      await votingV2.connect(admin).endElection();
      await expect(
        votingV2.connect(signer1).vote(1, "voter-uuid-xyz")
      ).to.be.revertedWith("Election is not active");
    });
  });
});
