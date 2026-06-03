
// Description: Header for a singly linked list that stores the colonization
//              history in insertion (chronological) order. Implemented from
//              scratch with raw pointers — STL containers are NOT used.


#ifndef LINKED_LIST_H
#define LINKED_LIST_H

#include <string>

// ---------------------------------------------------------------------------
// Node structure — matches the diagram in the project report:
//   [ x | y | owner | resources | next* ]
// ---------------------------------------------------------------------------
struct Node {
    int x;           // Column index (0-based)
    int y;           // Row index    (0-based)
    std::string owner;   // "player" or "ai"
    int resources;       // Resource value of the cell at colonization time
    Node* next;          // Pointer to the chronologically next entry
};

// ---------------------------------------------------------------------------
// LinkedList class — singly linked, head-and-tail tracked so that append is
// O(1) instead of O(n).
// ---------------------------------------------------------------------------
class LinkedList {
public:
    // Constructor: 
    LinkedList();

    // Destructor
    ~LinkedList();

    // append(x, y, owner, resources)
    //   Adds a new node at the TAIL of the list.

    void append(int x, int y, const std::string& owner, int resources);

    // remove_last()
    //   Removes the last node (most recent colonization).

    void remove_last();

    // print_all()
    //   Prints every node to stdout in insertion order.

    void print_all() const;

    // size()
    //   Returns the number of nodes currently in the list.

    int size() const;

    // get_head()
    //   Returns a const pointer to the first node (read-only traversal).
    const Node* get_head() const;

    // clear()
    //   Frees all nodes and resets the list to empty.

    void clear();

private:
    Node* head;   // First node (oldest colonization)
    Node* tail;   // Last  node (most recent colonization)
    int   count;  // Number of nodes currently stored
};

#endif 
