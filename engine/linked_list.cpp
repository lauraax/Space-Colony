// Team 14: Laura Paez, Nicolas Acero, Erik Fernandez
// Variant: Space Colony 

// Description: Singly linked list that stores colonization history.
//              All operations use raw pointers (new / delete).
//              STL list / vector are NOT used.

#include "linked_list.h"
#include <iostream>


// Constructor

LinkedList::LinkedList() : head(nullptr), tail(nullptr), count(0) {}


// Destructor
// Time  : O(n) — must free every heap-allocated node.
// Space : O(1) extra.

LinkedList::~LinkedList() {
    clear();
}


// append
//   Creates a new node and links it at the tail.

void LinkedList::append(int x, int y, const std::string& owner, int resources) {
    // Allocate and populate the new node
    Node* new_node = new Node();
    new_node->x         = x;
    new_node->y         = y;
    new_node->owner     = owner;
    new_node->resources = resources;
    new_node->next      = nullptr;   // will be the new tail

    if (tail == nullptr) {
        // List was empty — new node is both head and tail
        head = new_node;
        tail = new_node;
    } else {
        // Wire the current tail to point to the new node, then advance tail
        tail->next = new_node;
        tail       = new_node;
    }
    ++count;
}

// remove_last
//   Unlinks and deletes the tail node.
//   A singly linked list has no back-pointer, so we must walk to find the

void LinkedList::remove_last() {
    if (head == nullptr) return;   // empty list — nothing to do

    if (head == tail) {
        // Only one node in the list
        delete head;
        head  = nullptr;
        tail  = nullptr;
        count = 0;
        return;
    }

    // Walk until we reach the node just before the tail
    Node* current = head;
    while (current->next != tail) {
        current = current->next;
    }
    // current is now the second-to-last node
    delete tail;
    current->next = nullptr;
    tail          = current;
    --count;
}

// print_all
//   Traverses the list from head to tail and prints each node's data.

void LinkedList::print_all() const {
    const Node* current = head;
    int index = 0;
    while (current != nullptr) {
        std::cout << "[" << index << "] "
                  << "(" << current->x << "," << current->y << ") "
                  << "owner=" << current->owner << " "
                  << "resources=" << current->resources
                  << "\n";
        current = current->next;
        ++index;
    }
}


// size
//   Returns the node count maintained by append / remove_last / clear.

int LinkedList::size() const {
    return count;
}


// get_head
//   Exposes the head pointer for read-only external traversal.

const Node* LinkedList::get_head() const {
    return head;
}


// clear
//   Deletes every node and resets the list to an empty state.

void LinkedList::clear() {
    Node* current = head;
    while (current != nullptr) {
        Node* next = current->next;
        delete current;
        current = next;
    }
    head  = nullptr;
    tail  = nullptr;
    count = 0;
}
