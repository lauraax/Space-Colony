// Team 14: Laura Paez, Nicolas Acero, Erik Fernandez
// Variant: Space Colony 

// Description: AVL tree used to store colony resource data.
//              The resource value is the main key.
//              If two colonies have the same resources, their position is used.
//              The tree keeps itself balanced with rotations.

#include "tree.h"
#include <iostream>
#include <algorithm>   // std::max

// =============================================================================
// Constructor / Destructor
// =============================================================================

AVLTree::AVLTree() : root(nullptr), node_count(0) {}

AVLTree::~AVLTree() {
    clear();
}

// =============================================================================
// Public Interface
// =============================================================================

// Add a new colony to the tree.
// The recursive helper finds the right place and then rebalances the tree.
void AVLTree::insert(int resources, int energy_cost, int x, int y,
                     const std::string& owner) {
    root = insert_rec(root, resources, energy_cost, x, y, owner);
    ++node_count;
}

// Remove a colony from the tree.
// The helper handles the delete and updates the balance on the way back.
void AVLTree::remove(int resources, int x, int y) {
    int old_size = node_count;
    root = remove_rec(root, resources, x, y);
    // Decrement only if a node was actually removed.
    if (node_count == old_size) {
        // node_count is changed inside remove_rec when a node is found.
    }
}

// Return the node with the biggest resource value.
const AVLNode* AVLTree::find_max() const {
    if (root == nullptr) return nullptr;
    AVLNode* current = root;
    while (current->right != nullptr) {
        current = current->right;
    }
    return current;
}

// Return the node with the smallest resource value.
const AVLNode* AVLTree::find_min() const {
    return find_min_node(root);
}

// Find the owner's colony with the biggest resource value.
// Owner is not part of the tree order, so this checks the tree manually.
const AVLNode* AVLTree::find_max_by_owner(const std::string& owner) const {
    return find_max_owner_rec(root, owner, nullptr);
}

// Find the owner's colony with the smallest resource value.
const AVLNode* AVLTree::find_min_by_owner(const std::string& owner) const {
    return find_min_owner_rec(root, owner, nullptr);
}

// Print the tree from lowest to highest resource value.
void AVLTree::print_inorder() const {
    inorder_rec(root);
    std::cout << "\n";
}

// Return the number of nodes stored in the tree.
int AVLTree::size() const {
    return node_count;
}

// Delete all nodes and leave the tree empty.
void AVLTree::clear() {
    destroy_rec(root);
    root       = nullptr;
    node_count = 0;
}

// =============================================================================
// Private Helpers
// =============================================================================

// Return 0 for an empty node, otherwise return its height.
int AVLTree::get_height(AVLNode* node) const {
    return (node == nullptr) ? 0 : node->height;
}

// Balance is left height minus right height.
int AVLTree::get_balance(AVLNode* node) const {
    if (node == nullptr) return 0;
    return get_height(node->left) - get_height(node->right);
}

// Update the height after a change in one of the children.
void AVLTree::update_height(AVLNode* node) {
    if (node != nullptr) {
        node->height = 1 + std::max(get_height(node->left),
                                    get_height(node->right));
    }
}

// Rotate the subtree to the right around y.
//
//       y                x
//      / \              / \
//     x   T3    =>    T1   y
//    / \                  / \
//   T1  T2              T2  T3
AVLNode* AVLTree::rotate_right(AVLNode* y) {
    AVLNode* x  = y->left;
    AVLNode* T2 = x->right;

    x->right = y;
    y->left  = T2;

    update_height(y);   // y moved down, so update it first.
    update_height(x);

    return x;           // x is now the root of this subtree.
}

// Rotate the subtree to the left around x.
//
//     x                  y
//    / \                / \
//   T1   y    =>      x   T3
//       / \          / \
//      T2  T3       T1  T2
AVLNode* AVLTree::rotate_left(AVLNode* x) {
    AVLNode* y  = x->right;
    AVLNode* T2 = y->left;

    y->left  = x;
    x->right = T2;

    update_height(x);
    update_height(y);

    return y;
}

// Check the balance and use the needed rotation.
// The cases are left-left, left-right, right-right, and right-left.
AVLNode* AVLTree::rebalance(AVLNode* node) {
    update_height(node);
    int balance = get_balance(node);

    // Left-left case.
    if (balance > 1 && get_balance(node->left) >= 0) {
        return rotate_right(node);
    }
    // Left-right case.
    if (balance > 1 && get_balance(node->left) < 0) {
        node->left = rotate_left(node->left);
        return rotate_right(node);
    }
    // Right-right case.
    if (balance < -1 && get_balance(node->right) <= 0) {
        return rotate_left(node);
    }
    // Right-left case.
    if (balance < -1 && get_balance(node->right) > 0) {
        node->right = rotate_right(node->right);
        return rotate_left(node);
    }

    return node;   // Already balanced.
}

// -----------------------------------------------------------------------------
// Build the ordering key.
// Resources are the main value, and position breaks ties.
// -----------------------------------------------------------------------------
static int colony_key(int resources, int x, int y) {
    // This keeps each colony unique on the 8x8 board.
    return resources * 100 + (x * 8 + y);
}

// Insert a node using the same idea as a BST, then rebalance.
AVLNode* AVLTree::insert_rec(AVLNode* node, int resources, int energy_cost,
                              int x, int y, const std::string& owner) {
    // Empty spot found, so create the new node.
    if (node == nullptr) {
        AVLNode* new_node    = new AVLNode();
        new_node->resources  = resources;
        new_node->energy_cost = energy_cost;
        new_node->x          = x;
        new_node->y          = y;
        new_node->owner      = owner;
        new_node->left       = nullptr;
        new_node->right      = nullptr;
        new_node->height     = 1;
        return new_node;
    }

    int new_key  = colony_key(resources, x, y);
    int cur_key  = colony_key(node->resources, node->x, node->y);

    if (new_key < cur_key) {
        node->left  = insert_rec(node->left,  resources, energy_cost, x, y, owner);
    } else if (new_key > cur_key) {
        node->right = insert_rec(node->right, resources, energy_cost, x, y, owner);
    }
    // Duplicate keys are ignored. This should not happen during normal play.

    return rebalance(node);
}

// Return the leftmost node in this subtree.
AVLNode* AVLTree::find_min_node(AVLNode* node) const {
    if (node == nullptr) return nullptr;
    while (node->left != nullptr) {
        node = node->left;
    }
    return node;
}

// Delete a node from the tree and keep the tree balanced.
AVLNode* AVLTree::remove_rec(AVLNode* node, int resources, int x, int y) {
    if (node == nullptr) return nullptr;

    int target_key = colony_key(resources, x, y);
    int cur_key    = colony_key(node->resources, node->x, node->y);

    if (target_key < cur_key) {
        node->left  = remove_rec(node->left,  resources, x, y);
    } else if (target_key > cur_key) {
        node->right = remove_rec(node->right, resources, x, y);
    } else {
        // This is the node we need to delete.
        --node_count;

        if (node->left == nullptr || node->right == nullptr) {
            // The node has no child or only one child.
            AVLNode* child = (node->left != nullptr) ? node->left : node->right;
            delete node;
            return child;   // This can be nullptr when the node was a leaf.
        } else {
            // The node has two children, so use the next value in order.
            AVLNode* successor = find_min_node(node->right);
            // Copy successor data into the current node.
            node->resources   = successor->resources;
            node->energy_cost = successor->energy_cost;
            node->x           = successor->x;
            node->y           = successor->y;
            node->owner       = successor->owner;
            // Remove the copied successor from the right subtree.
            // Add one back because remove_rec will subtract it again.
            ++node_count;
            node->right = remove_rec(node->right,
                                     successor->resources,
                                     successor->x,
                                     successor->y);
        }
    }
    return rebalance(node);
}

// Delete nodes after deleting their children.
void AVLTree::destroy_rec(AVLNode* node) {
    if (node == nullptr) return;
    destroy_rec(node->left);
    destroy_rec(node->right);
    delete node;
}

// Print nodes in ascending resource order.
void AVLTree::inorder_rec(AVLNode* node) const {
    if (node == nullptr) return;
    inorder_rec(node->left);
    std::cout << "(" << node->x << "," << node->y << ") "
              << "owner=" << node->owner << " "
              << "resources=" << node->resources << "  ";
    inorder_rec(node->right);
}

// Look for the owner's colony with the biggest resource value.
// The right side is checked first because it usually has larger values.
const AVLNode* AVLTree::find_max_owner_rec(AVLNode* node,
                                            const std::string& owner,
                                            const AVLNode* best) const {
    if (node == nullptr) return best;

    // Check larger values first.
    best = find_max_owner_rec(node->right, owner, best);

    if (node->owner == owner) {
        if (best == nullptr || node->resources > best->resources) {
            best = node;
        }
    }

    best = find_max_owner_rec(node->left, owner, best);
    return best;
}

// Look for the owner's colony with the smallest resource value.
// The left side is checked first because it usually has smaller values.
const AVLNode* AVLTree::find_min_owner_rec(AVLNode* node,
                                            const std::string& owner,
                                            const AVLNode* best) const {
    if (node == nullptr) return best;

    best = find_min_owner_rec(node->left, owner, best);

    if (node->owner == owner) {
        if (best == nullptr || node->resources < best->resources) {
            best = node;
        }
    }

    best = find_min_owner_rec(node->right, owner, best);
    return best;
}
