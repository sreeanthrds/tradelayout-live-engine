# ✅ STEP 4 & 5 COMPLETE: Signal Nodes Updated to Use position_num

## 🎯 **Objective**
Update both **EntrySignalNode** and **ExitSignalNode** to use `position_num` from GPS instead of `reEntryNum` from context, while **keeping** the condition switching flexibility.

---

## 📋 **What Was Changed**

### **STEP 4: EntrySignalNode** (`strategy/nodes/entry_signal_node.py`)

#### **Before:**
```python
# Get reEntryNum from node state (context-propagated)
re_entry_num = int(self._get_node_state(context).get('reEntryNum', 0) or 0)
in_reentry_mode = re_entry_num > 0
```

#### **After:**
```python
# Get position_num from GPS
in_reentry_mode = self._is_in_reentry_mode(context)

def _is_in_reentry_mode(self, context):
    # Get position_id from child EntryNode
    position_id = entry_node.get_position_id(context)
    
    # Get position_num from GPS
    latest_position_num = gps.get_latest_position_num(position_id)
    
    # Re-entry mode if position_num > 0
    return latest_position_num > 0
```

#### **Key Changes:**
- ✅ Uses `position_num` from GPS (source of truth)
- ✅ **Keeps** condition switching (initial vs re-entry)
- ✅ Falls back to normal conditions if re-entry conditions not configured
- ✅ Removed error-throwing when re-entry conditions missing (now flexible)

---

### **STEP 5: ExitSignalNode** (`strategy/nodes/exit_signal_node.py`)

#### **Before:**
```python
# Get reEntryNum from node state (context-propagated)
in_reentry_mode = int(self._get_node_state(context).get('reEntryNum', 0) or 0) > 0
```

#### **After:**
```python
# Get position_num from GPS
in_reentry_mode = self._is_in_reentry_mode(context)

def _is_in_reentry_mode(self, context):
    # Get currently open position from GPS
    for pos_id, pos_data in gps.positions.items():
        if pos_data.get('status') == 'open':
            position_num = pos_data.get('position_num', 1)
            # Re-entry mode if position_num > 1
            return position_num > 1
    
    return False
```

#### **Key Changes:**
- ✅ Uses `position_num` from GPS (source of truth)
- ✅ **Keeps** condition switching (normal vs re-entry exit)
- ✅ Falls back to normal conditions if re-entry exit conditions not configured
- ✅ Checks position_num > 1 (position 2, 3, etc.)

---

## 🔄 **Condition Switching Logic (Kept)**

### **Why We Kept It:**
1. **Flexibility** - Allows different strategies for initial vs re-entry
2. **Backward Compatible** - Existing strategies continue to work
3. **No Harm** - If not used, just evaluates normal conditions
4. **User Choice** - Users can configure re-entry conditions or not

### **How It Works Now:**

#### **EntrySignalNode:**
```
position_num = 0 → Use normal entry conditions
position_num > 0 → Use re-entry entry conditions (if configured)
                   Otherwise use normal entry conditions
```

#### **ExitSignalNode:**
```
position_num = 1 → Use normal exit conditions
position_num > 1 → Use re-entry exit conditions (if configured)
                   Otherwise use normal exit conditions
```

---

## 📊 **Comparison: Old vs New**

| Aspect | OLD Behavior | NEW Behavior |
|--------|-------------|--------------|
| **Source** | `reEntryNum` from context | `position_num` from GPS ✅ |
| **Propagation** | Through context/node state | Direct from GPS ✅ |
| **Entry Check** | `reEntryNum > 0` | `position_num > 0` ✅ |
| **Exit Check** | `reEntryNum > 0` | `position_num > 1` ✅ |
| **Switching** | ✅ Kept | ✅ Kept |
| **Fallback** | ❌ Error if missing | ✅ Use normal conditions |
| **Reliability** | Context propagation | GPS (source of truth) ✅ |

---

## ✅ **Benefits of This Approach**

### **1. Single Source of Truth**
- `position_num` managed by GPS
- No context propagation needed
- More reliable and consistent

### **2. Better Architecture**
```
GPS → position_num → Signal Nodes
  ↓
EntryNode.maxEntries
  ↓
ReEntrySignalNode checks
```

### **3. Flexibility Preserved**
- Users can configure different conditions for re-entry
- Or use same conditions (by not configuring re-entry conditions)
- No breaking changes

### **4. Cleaner Code**
- No need to propagate `reEntryNum` through context
- Direct lookup from GPS
- Simpler state management

---

## 🔍 **Implementation Details**

### **EntrySignalNode Helper Method:**
```python
def _is_in_reentry_mode(self, context: Dict[str, Any]) -> bool:
    # Get position_id from child EntryNode
    entry_node = node_instances.get(self.children[0])
    position_id = entry_node.get_position_id(context)
    
    # Get position_num from GPS
    gps = context_manager.gps
    latest_position_num = gps.get_latest_position_num(position_id)
    
    # Re-entry mode if position_num > 0
    return latest_position_num > 0
```

**Logic:**
- `position_num = 0` → No positions yet, use normal entry conditions
- `position_num > 0` → Has positions, use re-entry entry conditions (if configured)

### **ExitSignalNode Helper Method:**
```python
def _is_in_reentry_mode(self, context: Dict[str, Any]) -> bool:
    # Get currently open position
    gps = context_manager.gps
    
    for pos_id, pos_data in gps.positions.items():
        if pos_data.get('status') == 'open':
            position_num = pos_data.get('position_num', 1)
            # Re-entry mode if position_num > 1
            return position_num > 1
    
    return False
```

**Logic:**
- `position_num = 1` → First position, use normal exit conditions
- `position_num > 1` → Re-entry position (2, 3, etc.), use re-entry exit conditions (if configured)

---

## 🎯 **Next Steps**

**STEP 6: Cleanup (Optional)**
- Remove `reEntryNum` from context propagation in `ContextAdapter`
- Remove `reEntryNum` increment logic from nodes
- Clean up any remaining references

**Note:** `reEntryNum` is still being incremented in some nodes for backward compatibility and tracking. STEP 6 will clean this up.

---

## ✨ **Status**
**STEP 4 & 5: ✅ COMPLETE** - Both signal nodes now use `position_num` from GPS while preserving condition switching flexibility!
