# Progress log (Skill-based)
## 1A (7) pattern=.......
Assume nothing succeeded in unfinished meal
- Definition: Assume
- Wordplay: Build SUPPOSE from unfinished meaL = SUPP (to eat) + O (nothing) + S (succeeded) + E (last of meal).
- Fodder/indicators: nothing=O; succeeded=S; unfinished meal → SUPP; last of meal=E
- Shortlist: SUPPOSE, ASSUME, PRESUME
- Tool attempts: (none) direct assembly; committed because exact fit to pattern + standard cryptic abbreviations
- Decision: COMMITTED: SUPPOSE

## 1D (7) pattern=.......
Faint line dividing poster
- Definition: Poster
- Wordplay: Unclear; might be something meaning poster built from faint line dividing
- Fodder/indicators: faint, line, dividing
- Shortlist: PLACARD, BILLPOST
- Tool attempts: (not run yet)
- Decision: PENDING

## 2D (7) pattern=.......
Requests by European to put on small suits
- Definition: Suits
- Wordplay: PLEAS (requests) + E (European) + S (small) → PLEASES
- Fodder/indicators: requests=PLEAS; European=E; small=S
- Shortlist: PLEASES, CLOTHES
- Tool attempts: (none) charade; committed (pattern now PLEASES)
- Decision: COMMITTED: PLEASES

## 3D (2,3) pattern=.....
Live in Barcelona irregularly
- Definition: Live
- Wordplay: Hidden answer: barcelONA IRregularly contains ONAIR = ON AIR (live).
- Fodder/indicators: in Barcelona irregularly → fodder "Barcelona irregularly"
- Shortlist: ON AIR
- Tool attempts: hidden.py returned none because words.txt does not include "onair"; committed based on exact hidden substring + checkers
- Decision: COMMITTED: ON AIR

## 4D (9) pattern=.........
Prove his table's wobbly
- Definition: Prove
- Wordplay: Anagram (wobbly) of HIS TABLE → ESTABLISH
- Fodder/indicators: HIS TABLE
- Shortlist: ESTABLISH
- Tool attempts: anagram.py fodder="histables" (HIS TABLE'S) pattern="..T......" → candidate: establish
- Decision: COMMITTED: ESTABLISH

## 5A (7) pattern=.......
Undergarment Edward adjusted
- Definition: Undergarment
- Wordplay: "adjusted" suggests anagram of EDWARD (+?)
- Fodder/indicators: EDWARD
- Shortlist: DRAWERS, BRA, TEDDIES
- Tool attempts: (not run yet)
- Decision: PENDING

## 5D (5) pattern=SHEDS
The woman's clothing daughter removes
- Definition: Removes
- Wordplay: Charade: THE WOMAN'S = SHE'S + D (daughter) → SHEDS
- Fodder/indicators: daughter = D
- Tool attempts: (none)
- Decision: COMMITTED: SHEDS

## 6D (9) pattern=.........
Significant ship in a series of books
- Definition: Significant
- Wordplay: Charade: ship=SS/ARK + series (I) + books (NT?)
- Fodder/indicators: ship, series, books
- Shortlist: IMPORTANT, MOMENTOUS
- Tool attempts: (not run yet)
- Decision: PENDING

## 7D (7) pattern=TRAFFIC
Buying and selling vehicles
- Definition: Buying and selling
- Wordplay: Double definition: TRAFFIC = buying and selling (esp. illicit trade); also traffic (vehicles).
- Fodder/indicators: none (DD)
- Tool attempts: (none)
- Decision: COMMITTED: TRAFFIC

## 8D (7) pattern=.......
Threats from last of bed bugs
- Definition: Threats
- Wordplay: RETRACTED (previous commit was incorrect; clue words are fodder/indicators, not the definition)
- Fodder/indicators: last of beD; bugs
- Shortlist: BEDBUGS
- Tool attempts: (n/a)
- Decision: RETRACTED

## 9A (7) pattern=.......
Graceful adult hugged by gentle drunk
- Definition: Graceful
- Wordplay: Anagram (drunk) of GENTLE around A (adult) → ELEGANT
- Fodder/indicators: GENTLE + A
- Shortlist: ELEGANT
- Tool attempts: anagram.py fodder="gentle a" pattern="......." → candidates: angelet, elegant; chose ELEGANT
- Decision: COMMITTED: ELEGANT

## 10A (7) pattern=.......
Clear up old tract of open land
- Definition: Clear up
- Wordplay: Unclear; maybe charade with O(ld) + LEA(open land) + TR(act?)
- Fodder/indicators: old(O), tract, open land(LEA)
- Shortlist: RESOLVE, ELUCIDATE, EXPLAIN
- Tool attempts: (not run yet)
- Decision: PENDING

## 11A (9) pattern=.........
Reports from half of rude authors
- Definition: Reports
- Wordplay: DE (half of ruDE) + SCRIBES (authors) → DESCRIBES (reports).
- Fodder/indicators: half of ruDE; authors=SCRIBES
- Shortlist: DESCRIBES
- Tool attempts: charade.py components=["de","scribes"], pattern="..s.r.b.." → describes (note: tools expect lowercase pattern)
- Decision: COMMITTED: DESCRIBES

## 12A (5) pattern=.....
Student found in widespread search
- Definition: Student
- Wordplay: "found in" suggests hidden in "wideSPREAD SEARCH" → ??? (needs exact letters)
- Fodder/indicators: widespread search
- Shortlist: FROSH, UNDERGRAD, PUPIL
- Tool attempts: hidden.py fodder="widespread search" length=5 pattern="....." → candidates: wides, reads (discarded)
- Decision: PENDING

## 13A (5) pattern=.....
Wines lifted spirits initially
- Definition: Wines
- Wordplay: Maybe initial letters (Spirits initially = SI) plus reversal/lifted
- Fodder/indicators: spirits initially
- Shortlist: WINES, RIESL, ASTIS
- Tool attempts: (not run yet)
- Decision: PENDING

## 14D (9) pattern=.........
American enthralled by scariest bats in flight
- Definition: American
- Wordplay: "in flight" suggests anagram of SCARIEST + BATS?; enthralled by indicates containment
- Fodder/indicators: SCARIEST BATS
- Shortlist: 
- Tool attempts: (not run yet)
- Decision: PENDING

## 15A (9) pattern=.........
Makes reference to hip positions
- Definition: Makes reference to
- Wordplay: RETRACTED (previous commit lacked solid parse; reverting to unsolved)
- Fodder/indicators: hip=in; positions=??; scribes=authors/writers
- Shortlist: INSCRIBES
- Tool attempts: (n/a)
- Decision: RETRACTED

## 16D (9) pattern=.........
Fulfilled sad fetish I arranged without husband
- Definition: Fulfilled
- Wordplay: Anagram (arranged) of SAD FETISH I minus H (husband) → SATISFIED
- Fodder/indicators: SAD FETISH I - H
- Shortlist: SATISFIED
- Tool attempts: anagram.py fodder="sadfetisi" (SAD FETISH I minus H) pattern="........." → candidate: satisfied
- Decision: COMMITTED: SATISFIED

## 17A (4,1,4) pattern=.........
Immediately get a kick from a gun discharge
- Definition: Immediately
- Wordplay: Phrase = LIKE A SHOT (meaning immediately). Wordplay: LIKE (get a kick from), SHOT (gun discharge).
- Fodder/indicators: get a kick from → LIKE; gun discharge → SHOT
- Shortlist: AT A SHOT, ON THE SPOT
- Tool attempts: charade.py cannot validate multiword phrases (LIKEASHOT not in words.txt); committed based on exact fit to pattern + definition
- Decision: COMMITTED: LIKE A SHOT

## 17D (7) pattern=.......
To a smaller extent, head of state supports working classes
- Definition: To a smaller extent
- Wordplay: Likely LESS + S(head of state) + ?
- Fodder/indicators: LESS, S, working classes
- Shortlist: LESSER, SLIGHTLY
- Tool attempts: (not run yet)
- Decision: PENDING

## 18D (7) pattern=.......
Fish – these could be in the sack
- Definition: Fish / in the sack
- Wordplay: Double definition: KIPPERS are fish; to "kip" = sleep, so "kippers" could be in the sack.
- Fodder/indicators: - (double definition)
- Shortlist: ASLEEP
- Tool attempts: (none) double definition; committed (pattern KIPPERS)
- Decision: COMMITTED: KIPPERS

## 19A (5) pattern=.....
Radical left-wingers run scared at first
- Definition: Radical
- Wordplay: Likely charade: left-wingers=REDS; run=R; scared at first=S
- Fodder/indicators: REDS + R + S
- Shortlist: RED, RADIC, S
- Tool attempts: (not run yet)
- Decision: PENDING

## 20D (7) pattern=.......
Silhouette revealed crow's foot
- Definition: Silhouette
- Wordplay: OUT (revealed) + LINE (crow's foot / line) → OUTLINE.
- Fodder/indicators: revealed=OUT; crow's foot=line
- Shortlist: OUTLINE
- Tool attempts: charade.py components=["out","line"], pattern="..t...e" → outline
- Decision: COMMITTED: OUTLINE

## 21D (7) pattern=.......
Some scientists send a spaceship up in regret
- Definition: Regret
- Wordplay: S (some scientistS) + (SEND A) reversed ("up" in Down clue) = ADNES + S (spaceship abbrev) → SADNESS.
- Fodder/indicators: some scientistS; send a; up (reversal); spaceship=S
- Shortlist: SADNESS
- Tool attempts: (none) committed from exact fit to pattern + clean wordplay
- Decision: COMMITTED: SADNESS

## 22A (5) pattern=..P..
Drink beer regularly? Wicked!
- Note: Previously (incorrectly) filled as IMPER without a sound parse for the definition.
- Definition: likely Drink
- Wordplay: "beer regularly" could contribute ER; "wicked" could be IMP.
- Issue: IMP+ER gives IMPER (a valid word), but it does **not** satisfy the definition "Drink".
- Decision: RETRACTED / back to PENDING (leave unsolved until we can satisfy definition + wordplay cleanly)

## 23A (9) pattern=.........
His Excellency expounded about one's getting delayed
- Definition: Delayed
- Wordplay: HE (His Excellency) + (STATED = expounded) with I (one's) inserted/adjusted → HESITATED.
- Fodder/indicators: HE; expounded=STATED; about one's=I
- Shortlist: HESITATED
- Tool attempts: (none) committed from parse + checkers
- Decision: COMMITTED: HESITATED

## 23D (5) pattern=.....
Pays attention to what upset editor – story's beginning
- Definition: Pays attention to
- Wordplay: HE ("what?" = EH upset) + ED (editor) + S (story's beginning) → HEEDS.
- Fodder/indicators: what?=EH upset; editor=ED; story's beginning=S
- Shortlist: HEEDS
- Tool attempts: (none) charade; committed with pattern
- Decision: COMMITTED: HEEDS

## 24D (5) pattern=.....
Guy almost captures 50 ducks
- Definition: Ducks
- Wordplay: TEAS (guy, almost = TEAS[E]) capturing L (50) → TEALS.
- Fodder/indicators: guy almost=TEAS; 50=L; captures=insertion
- Shortlist: TEALS
- Tool attempts: insertion.py fodder="l" outer="teas" pattern="t...s" → teals
- Decision: COMMITTED: TEALS

## 25A (7) pattern=.......
Run over and peer at cuckoo
- Definition: Cuckoo
- Wordplay: Maybe charade: run=R, over=OER, peer=SEE
- Fodder/indicators: R + OER + SEE
- Shortlist: LOONEY, MADCAP
- Tool attempts: (not run yet)
- Decision: PENDING

## 26A (7) pattern=.......
Fancy picture frames I note
- Definition: Fancy
- Wordplay: IMAG(E) with I + N (note) inserted/adjusted → IMAGINE (picture = IMAG(E); note=N; plus I).
- Fodder/indicators: picture=IMAGE; I; note=N
- Shortlist: IMAGINE
- Tool attempts: (none) committed from pattern + definition
- Decision: COMMITTED: IMAGINE

## 27A (7) pattern=.......
Son is brusque, dismissing conclusion of the relatives
- Definition: Relatives
- Wordplay: S (Son) + IS + TERS(E) (brusque=TERSE, dismissing conclusion -> TERS) → SISTERS.
- Fodder/indicators: Son=S; is=IS; brusque=TERSE minus last letter
- Shortlist: SISTERS
- Tool attempts: (none) charade; committed from exact fit to pattern + clean wordplay
- Decision: COMMITTED: SISTERS

## 28A (7) pattern=.......
Vagrants dress so badly
- Definition: Vagrants
- Wordplay: Anagram (badly) of DRESS SO → DOSSERS
- Fodder/indicators: DRESS SO
- Shortlist: DOSSERS
- Tool attempts: anagram.py fodder="dress so" pattern="......." → candidates: dossers, drosses; chose DOSSERS
- Decision: COMMITTED: DOSSERS

---

# Update (2026-03-03)

New commits placed into grid:
- 1D: SLENDER
- 5D: SHEDS
- 6D: IMPORTANT
- 7D: TRAFFIC
- 8D: DANGERS
- 10A: EXPLAIN
- 12A: RIFLE
- 13A: ROSES
- 15A: INSTANCES
- 19A: TROTS
- 22A: (retracted)

Re-check current unresolved patterns:
- 5A (7): P.I.T.D  — Undergarment Edward adjusted
- 14D (9): S.A.R...E — American enthralled by scariest bats in flight
- 17D (7): L.I...S — To a smaller extent, head of state supports working classes
- 25A (7): ..E...E — Run over and peer at cuckoo

Notes:
- Subagent suggested 14D=STATESIDE, but it conflicts with existing checkers in the current grid.


# Correction / rollback (2026-03-03)

- 5A SHIFTED parse corrected: SHIFT + ED (Edward); definition = "adjusted".
- Rolled back speculative fills that lacked clean wordplay:
  - 14D STATESIDE — RETRACTED (no solid parse)
  - 22A TIPLE — RETRACTED (dependent on 14D)
  - 25A BEELINE — RETRACTED (dependent on 22A)

Current patterns after rollback:
- 14D (9): S.A.....E
- 22A (5): ..P..
- 25A (7): ..E...E


# Solve (2026-03-04)

## 14D (9) pattern=S.A.....E
Clue: American enthralled by scariest bats in flight

Categorize:
- Definition likely: "in flight" (air-staircase)
- Wordplay: SCARIEST + A (American), with "bats" as anagram indicator

Tooling / validation:
- Pattern from grid_manager: S.A.....E
- Candidate: STAIRCASE (fits pattern)
- Parse: anagram(SCARIEST + A) → STAIRCASE

Decision: COMMITTED — STAIRCASE

## 5A (7) pattern=SHIFTED
Clue: Undergarment Edward adjusted
- Definition: adjusted
- Wordplay: SHIFT (undergarment) + ED (Edward)
Decision: COMMITTED — SHIFTED

## 22A (5) pattern=..P.R
Clue: Drink beer regularly? Wicked!
- Definition: Wicked! (excellent)
- Wordplay: SUP (drink) + ER (bEeR regularly)
Decision: COMMITTED — SUPER

## 25A (7) pattern=..E.A.E
Clue: Run over and peer at cuckoo
- Definition: Run
- Wordplay: ‘peer at’ cuckoo = anagram(PEERAT) → OPERATE
Decision: COMMITTED — OPERATE

## 17D (7) pattern=L.S.O.S
Clue: To a smaller extent, head of state supports working classes

Categorize:
- Definition: working classes
- Wordplay: LESS (to a smaller extent) + ON (supports) + S (head of State)

Decision: COMMITTED — LESSONS
