
const assert = require('assert');

function getWinnerStatus(candidates, totalVotes) {
    if (totalVotes === 0) return "NO VOTES";

    const sorted = [...candidates].sort((a, b) => b.voteCount - a.voteCount);
    const maxVotes = sorted[0].voteCount;
    const winners = sorted.filter(c => c.voteCount === maxVotes);

    if (winners.length === 1) {
        return `WINNER: ${winners[0].name.toUpperCase()}`;
    } else {
        const winnerNames = winners.map(c => c.name.toUpperCase()).join(" & ");
        return `TIE: ${winnerNames}`;
    }
}

// Case 1: Single Winner
const list1 = [{name: 'Alice', voteCount: 10}, {name: 'Bob', voteCount: 5}];
const res1 = getWinnerStatus(list1, 15);
console.log('Case 1 (Single):', res1);
assert.equal(res1, "WINNER: ALICE");

// Case 2: Tie
const list2 = [{name: 'Alice', voteCount: 10}, {name: 'Bob', voteCount: 10}, {name: 'Charlie', voteCount: 2}];
const res2 = getWinnerStatus(list2, 22);
console.log('Case 2 (Tie):', res2);
assert.equal(res2, "TIE: ALICE & BOB");

// Case 3: 3-way Tie
const list3 = [{name: 'Alice', voteCount: 10}, {name: 'Bob', voteCount: 10}, {name: 'Charlie', voteCount: 10}];
const res3 = getWinnerStatus(list3, 30);
console.log('Case 3 (3-way):', res3);
assert.equal(res3, "TIE: ALICE & BOB & CHARLIE");

// Case 4: Zero Votes
const res4 = getWinnerStatus([], 0);
console.log('Case 4 (Zero):', res4);
assert.equal(res4, "NO VOTES");

console.log("✅ All logic tests passed");
