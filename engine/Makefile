# =============================================================================
# Team: Laura Paez, Nicolas Acero, Erik Fernandez
# Variant: Space Colony (No. 14)
# Course: Computer Science I — Universidad Distrital Francisco José de Caldas
# File: Makefile
# =============================================================================

CXX      := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -O2
TARGET   := engine
SRCS     := main.cpp linked_list.cpp tree.cpp
OBJS     := $(SRCS:.cpp=.o)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
