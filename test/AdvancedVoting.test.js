import { expect } from "chai";
import { network } from "hardhat";

const { ethers } = await network.connect();

describe.skip("Voting contract — full unit tests (legacy - contract deleted)", function () {
  let Voting;
  let voting;
  let admin;
  let voter1;
  let voter2;
  let attacker;
  let addrs;

  beforeEach(async function () {
    [admin, voter1, voter2, attacker, ...addrs] = await ethers.getSigners();
    Voting = await ethers.getContractFactory("Voting", admin);
    voting = await Voting.deploy();
    await voting.waitForDeployment();
  });

  /**************************************************************************
   * Deployment
   **************************************************************************/
  describe("Deployment", function () {
    it("sets the deployer as admin", async function () {
      expect(await voting.admin()).to.equal(admin.address);
    });

    it("initializes election as active and totals to zero", async function () {
      expect(await voting.isElectionActive()).to.equal(true);
      expect(await voting.totalCandidates()).to.equal(0);
      expect(await voting.totalVotes()).to.equal(0);
    });
  });

  /**************************************************************************
   * Admin Functions
   **************************************************************************/
  describe("Admin functions", function () {
    it("admin can add candidates and emits CandidateAdded", async function () {
      await expect(voting.connect(admin).addCandidate("Alice"))
        .to.emit(voting, "CandidateAdded")
        .withArgs(1, "Alice");

      const candidate = await voting.getCandidate(1);
      expect(candidate[0]).to.equal(1); // id
      expect(candidate[1]).to.equal("Alice"); // name
      expect(candidate[2]).to.equal(0); // voteCount
      expect(await voting.totalCandidates()).to.equal(1);
    });

    it("non-admin cannot add candidates", async function () {
      await expect(
        voting.connect(attacker).addCandidate("Mallory")
      ).to.be.revertedWith("Only admin can perform this action.");
    });

    it("admin can authorize voters and emits VoterAuthorized", async function () {
      await expect(voting.connect(admin).authorizeVoter(voter1.address))
        .to.emit(voting, "VoterAuthorized")
        .withArgs(voter1.address);

      const info = await voting.getVoterInfo(voter1.address);
      expect(info[0]).to.equal(true); // isAuthorized
      expect(info[1]).to.equal(false); // hasVoted
      expect(info[2]).to.equal(0); // votedCandidateId
    });

    it("non-admin cannot authorize voters", async function () {
      await expect(
        voting.connect(attacker).authorizeVoter(voter1.address)
      ).to.be.revertedWith("Only admin can perform this action.");
    });

    it("cannot authorize zero address", async function () {
      await expect(
        voting.connect(admin).authorizeVoter(ethers.ZeroAddress)
      ).to.be.revertedWith("Invalid voter address.");
    });

    it("cannot re-authorize an already authorized voter", async function () {
      await voting.connect(admin).authorizeVoter(voter1.address);
      await expect(
        voting.connect(admin).authorizeVoter(voter1.address)
      ).to.be.revertedWith("Voter is already authorized.");
    });
  });

  /**************************************************************************
   * Voter Authorization
   **************************************************************************/
  describe("Voter Authorization", function () {
    beforeEach(async function () {
      // add a candidate so voting is meaningful
      await voting.connect(admin).addCandidate("Alice");
    });

    it("authorized voter can vote", async function () {
      await voting.connect(admin).authorizeVoter(voter1.address);

      await expect(voting.connect(voter1).vote(1))
        .to.emit(voting, "VoteCast")
        .withArgs(voter1.address, 1);

      const candidate = await voting.getCandidate(1);
      expect(candidate[2]).to.equal(1); // voteCount
      expect(await voting.totalVotes()).to.equal(1);

      const voterInfo = await voting.getVoterInfo(voter1.address);
      expect(voterInfo[0]).to.equal(true);
      expect(voterInfo[1]).to.equal(true);
      expect(voterInfo[2]).to.equal(1);
    });

    it("unauthorized voter cannot vote", async function () {
      await expect(voting.connect(voter2).vote(1)).to.be.revertedWith(
        "You are not authorized to vote."
      );
    });
  });

  /**************************************************************************
   * Voting Logic
   **************************************************************************/
  describe("Voting logic", function () {
    beforeEach(async function () {
      // two candidates
      await voting.connect(admin).addCandidate("Alice");
      await voting.connect(admin).addCandidate("Bob");

      // authorize two voters
      await voting.connect(admin).authorizeVoter(voter1.address);
      await voting.connect(admin).authorizeVoter(voter2.address);
    });

    it("successful voting increments candidate votes and totalVotes", async function () {
      await voting.connect(voter1).vote(1);
      await voting.connect(voter2).vote(2);

      const cand1 = await voting.getCandidate(1);
      const cand2 = await voting.getCandidate(2);

      expect(cand1[2]).to.equal(1);
      expect(cand2[2]).to.equal(1);
      expect(await voting.totalVotes()).to.equal(2);
    });

    it("prevents double voting (same voter cannot vote twice)", async function () {
      await voting.connect(voter1).vote(1);
      await expect(voting.connect(voter1).vote(2)).to.be.revertedWith(
        "You have already voted."
      );
    });

    it("rejects votes for invalid candidate IDs (0 and > totalCandidates)", async function () {
      await expect(voting.connect(voter1).vote(0)).to.be.revertedWith(
        "Invalid candidate ID."
      );
      await expect(voting.connect(voter1).vote(3)).to.be.revertedWith(
        "Invalid candidate ID."
      );
    });
  });

  /**************************************************************************
   * Election Lifecycle
   **************************************************************************/
  describe("Election lifecycle", function () {
    it("cannot end election with no candidates", async function () {
      await expect(voting.connect(admin).endElection()).to.be.revertedWith(
        "Cannot end election with no candidates."
      );
    });

    it("votes can only be cast when election is active", async function () {
      // add candidate and authorize a voter
      await voting.connect(admin).addCandidate("Alice");
      await voting.connect(admin).authorizeVoter(voter1.address);

      // admin ends election
      await voting.connect(admin).endElection();

      // election is inactive now
      expect(await voting.isElectionActive()).to.equal(false);

      // voting should be blocked
      await expect(voting.connect(voter1).vote(1)).to.be.revertedWith(
        "Election has ended."
      );
    });

    it("only admin can call endElection", async function () {
      await voting.connect(admin).addCandidate("Alice");
      await expect(voting.connect(attacker).endElection()).to.be.revertedWith(
        "Only admin can perform this action."
      );
    });

    it("endElection emits ElectionEnded with correct winner details", async function () {
      // Setup: 3 candidates, 3 voters. Voter1->Cand1, Voter2->Cand1, Voter3->Cand2
      await voting.connect(admin).addCandidate("Alice"); // id 1
      await voting.connect(admin).addCandidate("Bob");   // id 2
      await voting.connect(admin).addCandidate("Carol"); // id 3

      // authorize voters (use voter1, voter2, voter3 alias from addrs[0])
      const voter3 = addrs[0];
      await voting.connect(admin).authorizeVoter(voter1.address);
      await voting.connect(admin).authorizeVoter(voter2.address);
      await voting.connect(admin).authorizeVoter(voter3.address);

      await voting.connect(voter1).vote(1);
      await voting.connect(voter2).vote(1);
      await voting.connect(voter3).vote(2);

      // End election as admin - should emit ElectionEnded for winner = candidate 1 (Alice)
      await expect(voting.connect(admin).endElection())
        .to.emit(voting, "ElectionEnded")
        .withArgs(1, "Alice", 2);

      // election should be inactive
      expect(await voting.isElectionActive()).to.equal(false);
    });
  });

  /**************************************************************************
   * Winner Calculation
   **************************************************************************/
  describe("Winner calculation", function () {
    it("getWinner / getWinnerDetails works only after election ended and returns correct result", async function () {
      // add candidates
      await voting.connect(admin).addCandidate("Alice");
      await voting.connect(admin).addCandidate("Bob");

      // authorize voters: voter1 and voter2
      await voting.connect(admin).authorizeVoter(voter1.address);
      await voting.connect(admin).authorizeVoter(voter2.address);

      // split votes so Bob wins (2 votes)
      await voting.connect(voter1).vote(2);
      await voting.connect(voter2).vote(2);

      // trying to call getWinner before ending election should revert due to electionInactive modifier
      await expect(voting.getWinner()).to.be.revertedWith("Election is still active.");

      // end election
      await voting.connect(admin).endElection();

      // Now getWinner should return id 2
      const winnerId = await voting.getWinner();
      expect(winnerId).to.equal(2);

      // getWinnerDetails should return (id, name, voteCount)
      const details = await voting.getWinnerDetails();
      expect(details[0]).to.equal(2);
      expect(details[1]).to.equal("Bob");
      expect(details[2]).to.equal(2);
    });

    it("getAllCandidates returns full candidate list", async function () {
      await voting.connect(admin).addCandidate("Alice");
      await voting.connect(admin).addCandidate("Bob");
      await voting.connect(admin).addCandidate("Carol");

      const all = await voting.getAllCandidates();
      expect(all.length).to.equal(3);
      expect(all[0].id).to.equal(1);
      expect(all[0].name).to.equal("Alice");
      expect(all[1].id).to.equal(2);
      expect(all[2].name).to.equal("Carol");
    });
  });
});
