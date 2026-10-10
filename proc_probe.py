#!/usr/bin/env python3
"""
Process Probe - Validation script for Autobot shutdown
Monitors process tree and validates clean shutdown
"""

import psutil, os, sys, time, json
from typing import Dict, List

class ProcessProbe:
    def __init__(self, main_pid = None):
        self.main_pid = main_pid or os.getpid()
        self.initial_tree = {}
        self.final_tree = {}
        
    def capture_tree(self) -> Dict:
        """Capture current process tree"""
        tree = {}
        try:
            main_proc = psutil.Process(self.main_pid)
            tree[self.main_pid] = {
                'name': main_proc.name(),
                'cmdline': ' '.join(main_proc.cmdline()) if main_proc.cmdline() else '',
                'status': main_proc.status(),
                'children': []
            }
            
            # Get all descendants recursively  
            children = main_proc.children(recursive=True)
            for child in children:
                try:
                    tree[child.pid] = {
                        'name': child.name(),
                        'cmdline': ' '.join(child.cmdline()) if child.cmdline() else '',
                        'status': child.status(),
                        'parent_pid': child.ppid()
                    }
                    tree[self.main_pid]['children'].append(child.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"[PROBE] Error capturing tree: {e}")
            
        return tree
        
    def capture_initial(self):
        """Capture initial process state"""
        print(f"[PROBE] Capturing initial process tree for PID {self.main_pid}")
        self.initial_tree = self.capture_tree()
        self._log_tree("INITIAL", self.initial_tree)
        
    def capture_final(self):
        """Capture final process state after shutdown"""
        print(f"[PROBE] Capturing final process tree...")
        time.sleep(2)  # Allow processes to terminate
        self.final_tree = self.capture_tree()
        self._log_tree("FINAL", self.final_tree)
        
    def validate_shutdown(self) -> bool:
        """Validate clean shutdown - returns True if no orphans"""
        orphans = []
        
        for pid, info in self.initial_tree.items():
            if pid == self.main_pid:
                continue  # Main process expected to exit
                
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    orphans.append({
                        'pid': pid,
                        'name': info['name'],
                        'cmdline': info['cmdline'],
                        'status': proc.status()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass  # Process properly terminated
                
        if orphans:
            print(f"[PROBE] ❌ SHUTDOWN FAILED - {len(orphans)} orphan processes:")
            for orphan in orphans:
                print(f"  PID {orphan['pid']}: {orphan['name']} - {orphan['cmdline']}")
            return False
        else:
            print("[PROBE] ✅ CLEAN SHUTDOWN - No orphan processes detected")
            return True
            
    def _log_tree(self, phase: str, tree: Dict):
        """Log process tree to file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"process_tree_{phase.lower()}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(tree, f, indent=2)
            
        print(f"[PROBE] {phase} tree saved to {filename}")
        print(f"[PROBE] {phase} tree summary:")
        for pid, info in tree.items():
            status = info.get('status', 'unknown')
            name = info.get('name', 'unknown')
            print(f"  PID {pid}: {name} [{status}]")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--monitor':
            # Monitor mode - capture initial state
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else os.getppid()
            probe = ProcessProbe(pid)
            probe.capture_initial()
            
        elif sys.argv[1] == '--validate':
            # Validation mode - check for orphans
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else None
            if not pid:
                print("[PROBE] Error: PID required for validation")
                sys.exit(1)
                
            probe = ProcessProbe(pid)
            probe.capture_initial()  # Capture what we can find
            time.sleep(3)  # Wait for shutdown to complete
            success = probe.validate_shutdown()
            sys.exit(0 if success else 1)
            
        elif sys.argv[1] == '--kill-orphans':
            # Emergency cleanup mode
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else None
            if not pid:
                print("[PROBE] Error: PID required for cleanup")
                sys.exit(1)
                
            probe = ProcessProbe(pid)
            tree = probe.capture_tree()
            
            for child_pid in tree.get(pid, {}).get('children', []):
                try:
                    proc = psutil.Process(child_pid)
                    print(f"[PROBE] Force killing orphan PID {child_pid}: {proc.name()}")
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
    else:
        print("Usage:")
        print("  python proc_probe.py --monitor [PID]     # Monitor initial state")
        print("  python proc_probe.py --validate PID      # Validate shutdown")
        print("  python proc_probe.py --kill-orphans PID  # Emergency cleanup")

if __name__ == "__main__":
    main()
