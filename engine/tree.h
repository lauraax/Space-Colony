// Team 14: Laura Paez, Nicolas Acero, Erik Fernandez
// Variant: Space Colony 

// Description: Header for an AVL tree that stores the active colonies.
//              Colonies are ordered by resources, with position as a tiebreaker.
//              The tree balances itself after inserts and deletes.
//              It is built with raw pointers, without STL map or set.


#ifndef TREE_H
#define TREE_H

#include <string>

// ---------------------------------------------------------------------------
// AVL tree node. It matches the node diagram in the project report:
//   [ resources | cost | x | y | owner | left* | right* | height ]
// The key used for ordering is 'resources'.
// When resources are equal, (x * 8 + y) is used as a tiebreaker so that
// every colony has its own place in the tree.
// ---------------------------------------------------------------------------
struct AVLNode {
    int resources;       // Resource value used for ordering
    int energy_cost;     // Energy cost associated with the cell
    int x;               // Column index
    int y;               // Row index
    std::string owner;   // "player" or "ai"
    AVLNode* left;       // Left subtree with smaller values
    AVLNode* right;      // Right subtree with larger values
    int height;          // Height of this subtree (leaf = 1)
};

// ---------------------------------------------------------------------------
// AVLTree class.
// The tree keeps itself balanced after every insert and delete.
// ---------------------------------------------------------------------------
class AVLTree {
public:
    // Creates an empty tree.
    AVLTree();

    // Frees all nodes when the tree is destroyed.
    ~AVLTree();

    // Inserts a new colony and keeps the tree balanced.
    void insert(int resources, int energy_cost, int x, int y,
                const std::string& owner);

    // Removes a colony using its resources and position.
    void remove(int resources, int x, int y);

    // Returns the colony with the greatest resource value.
    // Returns nullptr if the tree is empty.
    const AVLNode* find_max() const;

    // Returns the colony with the smallest resource value.
    const AVLNode* find_min() const;

    // Returns the owner's colony with the greatest resource value.
    // Returns nullptr if that owner has no colonies.
    const AVLNode* find_max_by_owner(const std::string& owner) const;

    // Returns the owner's colony with the smallest resource value.
    // Returns nullptr if that owner has no colonies.
    const AVLNode* find_min_by_owner(const std::string& owner) const;

    // Prints all colonies from lowest to highest resource value.
    void print_inorder() const;

    // Returns how many colonies are stored in the tree.
    int size() const;

    // Frees all nodes and leaves the tree empty.
    void clear();

private:
    AVLNode* root;
    int      node_count;

    // Internal helpers. Most of them work on the subtree that starts at 'node'.

    int  get_height(AVLNode* node) const;
    int  get_balance(AVLNode* node) const;
    void update_height(AVLNode* node);

    AVLNode* rotate_right(AVLNode* y);
    AVLNode* rotate_left(AVLNode* x);
    AVLNode* rebalance(AVLNode* node);

    AVLNode* insert_rec(AVLNode* node, int resources, int energy_cost,
                        int x, int y, const std::string& owner);
    AVLNode* remove_rec(AVLNode* node, int resources, int x, int y);
    AVLNode* find_min_node(AVLNode* node) const;

    void destroy_rec(AVLNode* node);
    void inorder_rec(AVLNode* node) const;

    const AVLNode* find_max_owner_rec(AVLNode* node, const std::string& owner,
                                      const AVLNode* best) const;
    const AVLNode* find_min_owner_rec(AVLNode* node, const std::string& owner,
                                      const AVLNode* best) const;
};

#endif // TREE_H
