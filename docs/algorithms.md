# FactoryTwin — Algorithms & Multi-Agent Coordination

## 1. A* Pathfinding Algorithm

### Heuristic Function
For a 4-directional grid graph where agents move orthogonally between adjacent cells with uniform edge cost $c = 1$, the Manhattan distance heuristic is used:

$$h(n) = |x_n - x_{\text{goal}}| + |y_n - y_{\text{goal}}|$$

### Properties
1. **Admissibility**: Because orthogonal movements require at least $|x_n - x_{\text{goal}}| + |y_n - y_{\text{goal}}|$ steps to reach the destination in the absence of obstacles, $h(n) \le h^*(n)$ always holds.
2. **Consistency (Monotonicity)**: For every neighbor $n'$ of $n$:
   $$h(n) \le c(n, n') + h(n') = 1 + h(n')$$
   Because the heuristic is consistent, the first time a node is expanded from the priority queue, the shortest path to it has been found, preventing redundant re-expansions.
3. **Complexity**:
   - Time Complexity: $O(|E| + |V| \log |V|)$ using a binary min-heap (`heapq`).
   - Space Complexity: $O(|V|)$ to maintain open and closed sets.

### BFS Baseline Verification
In unweighted 4-directional grid graphs, Breadth-First Search (BFS) is provably optimal. In automated unit tests (`backend/tests/test_pathfinding.py`), every generated route is benchmarked against BFS to confirm that:
- $\text{cost}(A^*) = \text{cost}(\text{BFS})$
- $\text{nodes\_expanded}(A^*) \le \text{nodes\_expanded}(\text{BFS})$

---

## 2. Multi-Agent Fleet Movement Coordination

When multiple autonomous mobile robots share a factory grid, individual shortest paths can lead to collisions. FactoryTwin implements a centralized movement coordinator that guarantees safety under explicit rules.

### Safety Invariants Enforced
1. **No Vertex Conflicts**: No two robots may occupy the exact same coordinate $(x, y)$ at simulation tick $t$.
2. **No Edge Conflicts (Head-on Swaps)**: If Robot $A$ is at $u$ and intends to move to $v$, and Robot $B$ is at $v$ and intends to move to $u$, the movement is strictly rejected.
3. **No Traversing Obstacles**: Both static racking and dynamic obstacles reject planned movements.

### Coordination Step Algorithm
Each simulation tick advances via the following deterministic pipeline:
1. **Intent Collection**: For each active robot, query its intended next waypoint $p_{\text{target}}$.
2. **Priority Ordering**: Robots are ordered deterministically by:
   - State weight (INSPECTING > MOVING with task > MOVING idle > WAITING/IDLE).
   - Tie-breaker: Robot ID string sort.
3. **Reservation & Edge Check**:
   - Stationary robots reserve their current positions.
   - For each moving robot in priority order:
     - Check for edge swap with all other robots. If conflict detected, robot yields and increments wait counter.
     - Check if $p_{\text{target}}$ is already reserved. If reserved, robot yields.
     - If safe, approve move and reserve $p_{\text{target}}$.
4. **Deadlock Recovery & Bounded Waiting**:
   - If a robot is forced to wait for $\ge 2$ consecutive ticks due to a blocker, automatic route replanning is triggered.
   - The replanner calls $A^*$ with the blocker's position marked as forbidden.
   - If an alternate route exists around the congestion, the robot switches paths immediately; otherwise, it holds safe waiting state.

---

## 3. Production Task Scheduling Policies

FactoryTwin implements pluggable scheduling strategies:

### 1. FIFO (First-In, First-Out)
- Queues production orders by creation timestamp.
- Assigns the oldest pending task to the first available idle robot in fleet order.
- **Strengths**: Simple, eliminates task starvation.
- **Weaknesses**: May assign an AGV on the opposite side of the warehouse, resulting in high transit latency.

### 2. Nearest Available Robot
- For each pending task, calculates true topological shortest-path distance using $A^*$ from all eligible idle AGVs to the pickup bay.
- Assigns the closest robot, with deterministic tie-breaking.
- **Strengths**: Minimizes empty travel distance, decreases average order cycle time by ~24%.
