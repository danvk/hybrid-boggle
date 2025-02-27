# Try to speed up ibuckets by explicitly constructing an evaluation tree.

from boggle.board_class_boggler import BoardClassBoggler
from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.eval_tree import CHOICE_NODE, ROOT_NODE, EvalNode, create_eval_node_arena_py
from boggle.ibuckets import ScoreDetails
from boggle.trie import PyTrie


class TreeBuilder(BoardClassBoggler):
    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)

    def BuildTree(self, arena=None, dedupe=False):
        root = EvalNode()
        self.root = root
        root.letter = ROOT_NODE
        root.cell = 0  # irrelevant
        root.points = 0
        self.details_ = ScoreDetails(0, 0, -1)
        self.used_ = 0
        self.runs_ = self.trie_.Mark() + 1
        self.trie_.SetMark(self.runs_)
        self.node_cache = {}
        self.dedupe = dedupe

        for i in range(len(self.bd_)):
            child = EvalNode()
            child.letter = CHOICE_NODE
            child.cell = i
            score = self.DoAllDescents(i, 0, self.trie_, child)
            if score > 0:
                self.details_.max_nomark += score
                root.children.append(child)
                if len(self.bd_[i]) > 1:
                    # TODO: consolidate this with similar code in DoDFS
                    child.choice_mask |= 1 << i
                root.choice_mask |= child.choice_mask
        root.bound = self.details_.max_nomark
        # print(f"build tree node cache size: {len(self.node_cache)}")
        self.node_cache = {}
        return root

    def DoAllDescents(self, idx: int, length: int, t: PyTrie, node: EvalNode):
        max_score = 0

        for j, char in enumerate(self.bd_[idx]):
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                child = EvalNode()
                child.cell = idx
                child.letter = j
                tscore = self.DoDFS(
                    idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc), child
                )
                child = self.get_canonical_node(child)
                if tscore > 0:
                    max_score = max(max_score, tscore)
                    node.children.append(child)
                    node.choice_mask |= child.choice_mask
        node.bound = max_score
        node.points = 0
        return max_score

    def DoDFS(self, i: int, length: int, t: PyTrie, node: EvalNode):
        score = 0
        self.used_ ^= 1 << i

        for idx in self.neighbors[i]:
            if not self.used_ & (1 << idx):
                neighbor = EvalNode()
                neighbor.letter = CHOICE_NODE
                neighbor.cell = idx
                if len(self.bd_[idx]) > 1:
                    neighbor.choice_mask = 1 << idx
                tscore = self.DoAllDescents(idx, length, t, neighbor)
                neighbor = self.get_canonical_node(neighbor)
                if tscore > 0:
                    score += tscore
                    node.children.append(neighbor)
                    node.choice_mask |= neighbor.choice_mask

        node.points = 0
        if t.IsWord():
            word_score = SCORES[length]
            node.points = word_score
            node.trie_node = t
            score += word_score
            if t.Mark() != self.runs_:
                self.details_.sum_union += word_score
                t.SetMark(self.runs_)
        elif len(node.children) == 1:
            # COUNTS["singleton children"] += 1
            # node.assign_from(node.children[0])
            pass

        self.used_ ^= 1 << i
        node.bound = score
        return score

    def SumUnion(self):
        return self.details_.sum_union

    def get_canonical_node(self, node: EvalNode):
        if not self.dedupe:
            return node
        h = node.structural_hash()
        prev = self.node_cache.get(h)
        if prev:
            return prev
        self.node_cache[h] = node
        return node

    def create_arena(self):
        return create_eval_node_arena_py()

    def create_vector_arena(self):
        return create_eval_node_arena_py()
