# component_manager.py
import os
import shutil
import re
import yaml
from yaml import SafeLoader
from os.path import join
from typing import Set, Optional, Dict, Any, List


class ComponentLogger:
    """Handles logging functionality for component operations."""
    
    def __init__(self):
        self.component_changes: List[str] = []
    
    def log_change(self, message: str) -> None:
        """Log a component change with simple console output."""
        self.component_changes.append(message)
        print(f"[ComponentManager] {message}")
    
    def get_changes(self) -> List[str]:
        """Get all logged changes."""
        return self.component_changes
    
    def get_change_count(self) -> int:
        """Get the number of changes logged."""
        return len(self.component_changes)


class ComponentYamlHandler:
    """Handles YAML file operations for component configuration."""
    
    def __init__(self, logger: ComponentLogger):
        self.logger = logger
    
    def get_or_create_component_yml(self, arduino_framework_dir: str, project_src_dir: str) -> str:
        """Get path to idf_component.yml, creating it if necessary."""
        # Try Arduino framework first
        framework_yml = join(arduino_framework_dir, "idf_component.yml")
        if os.path.exists(framework_yml):
            self._create_backup(framework_yml)
            return framework_yml
        
        # Try project source directory
        project_yml = join(project_src_dir, "idf_component.yml")
        if os.path.exists(project_yml):
            self._create_backup(project_yml)
            return project_yml
        
        # Create new file in project source
        self._create_default_component_yml(project_yml)
        self.logger.log_change(f"Created new component.yml file at {project_yml}")
        return project_yml
    
    def load_component_yml(self, file_path: str) -> Dict[str, Any]:
        """Load and parse idf_component.yml file."""
        try:
            with open(file_path, "r") as f:
                return yaml.load(f, Loader=SafeLoader) or {"dependencies": {}}
        except Exception:
            return {"dependencies": {}}
    
    def save_component_yml(self, file_path: str, data: Dict[str, Any]) -> None:
        """Save component data to YAML file."""
        try:
            with open(file_path, "w") as f:
                yaml.dump(data, f)
            self.logger.log_change(f"Saved component configuration to {file_path}")
        except Exception as e:
            self.logger.log_change(f"Error saving component configuration: {str(e)}")
    
    def _create_backup(self, file_path: str) -> None:
        """Create backup of a file."""
        backup_path = f"{file_path}.orig"
        if not os.path.exists(backup_path):
            shutil.copy(file_path, backup_path)
            self.logger.log_change(f"Created backup: {backup_path}")
    
    def _create_default_component_yml(self, file_path: str) -> None:
        """Create a default idf_component.yml file."""
        default_content = {
            "dependencies": {
                "idf": ">=5.1"
            }
        }
        
        with open(file_path, 'w') as f:
            yaml.dump(default_content, f)


class ProjectAnalyzer:
    """Analyzes project dependencies and component usage."""
    
    def __init__(self, env):
        self.env = env
        self._project_components_cache = None
    
    def analyze_project_dependencies(self) -> Set[str]:
        """Analyze project files to detect actually used components/libraries."""
        used_components = set()
        
        try:
            # Analyze project source files
            src_dir = self.env.subst("$PROJECT_SRC_DIR")
            if os.path.exists(src_dir):
                for root, dirs, files in os.walk(src_dir):
                    for file in files:
                        if file.endswith(('.cpp', '.c', '.h', '.hpp', '.ino')):
                            file_path = os.path.join(root, file)
                            used_components.update(self._extract_components_from_file(file_path))
            
            # Analyze lib_deps for explicit dependencies (if present)
            lib_deps = self.env.GetProjectOption("lib_deps", [])
            if isinstance(lib_deps, str):
                lib_deps = [lib_deps]
            
            for dep in lib_deps:
                used_components.update(self._extract_components_from_lib_dep(str(dep)))
                
        except Exception:
            pass
        
        return used_components
    
    def is_component_used_in_project(self, lib_name: str) -> bool:
        """Check if a component/library is actually used in the project."""
        # Cache project analysis for performance
        if self._project_components_cache is None:
            self._project_components_cache = self.analyze_project_dependencies()
        
        lib_name_lower = lib_name.lower()
        
        # Direct match
        if lib_name_lower in self._project_components_cache:
            return True
        
        # Partial match for related components
        for used_component in self._project_components_cache:
            if lib_name_lower in used_component or used_component in lib_name_lower:
                return True
        
        return False
    
    def _extract_components_from_file(self, file_path: str) -> Set[str]:
        """Extract component usage from a single file by analyzing includes and function calls."""
        components = set()
        
        # Component detection patterns - maps component names to code patterns
        component_patterns = {
            'bt': ['bluetooth', 'ble', 'nimble', 'bt_', 'esp_bt', 'esp_ble'],
            'esp_wifi': ['wifi', 'esp_wifi', 'tcpip_adapter'],
            'esp_dsp': ['dsps_', 'esp_dsp', 'fft2r', 'dsps_fft2r'],
            'esp_http_client': ['esp_http_client', 'http_client'],
            'esp_https_ota': ['esp_https_ota', 'esp_ota'],
            'mdns': ['mdns', 'esp_mdns'],
            'mqtt': ['mqtt', 'esp_mqtt'],
            'spiffs': ['spiffs', 'esp_spiffs'],
            'fatfs': ['fatfs', 'ff.h'],
            'nvs_flash': ['nvs', 'nvs_flash'],
            'esp_timer': ['esp_timer', 'timer_'],
            'driver': ['gpio_', 'uart_', 'spi_', 'i2c_', 'adc_', 'dac_'],
            'esp_camera': ['esp_camera', 'camera.h'],
            'esp_now': ['esp_now', 'espnow'],
            'esp_smartconfig': ['smartconfig', 'esp_smartconfig'],
            'esp_eth': ['esp_eth', 'ethernet'],
            'esp_websocket_client': ['websocket', 'esp_websocket'],
            'cjson': ['cjson', 'json'],
            'mbedtls': ['mbedtls', 'ssl'],
            'openssl': ['openssl']
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                
                for component, patterns in component_patterns.items():
                    if any(pattern in content for pattern in patterns):
                        components.add(component)
                        
        except Exception:
            pass
        
        return components
    
    def _extract_components_from_lib_dep(self, lib_dep: str) -> Set[str]:
        """Extract components from lib_deps entry by mapping library names to ESP-IDF components."""
        components = set()
        lib_dep_upper = lib_dep.upper()
        
        # Map lib_deps entries to ESP-IDF components
        lib_dep_mapping = {
            'bt': ['BLE', 'BT', 'BLUETOOTH', 'NIMBLE'],
            'esp_wifi': ['WIFI', 'ASYNCTCP', 'ESPASYNCWEBSERVER'],
            'esp_dsp': ['DSP', 'FFT', 'JPEG'],
            'esp_http_client': ['HTTP', 'HTTPCLIENT'],
            'mqtt': ['MQTT', 'PUBSUB'],
            'esp_camera': ['CAMERA', 'ESP32CAM'],
            'esp_now': ['ESPNOW', 'ESP_NOW'],
            'mdns': ['MDNS'],
            'esp_eth': ['ETHERNET']
        }
        
        for component, keywords in lib_dep_mapping.items():
            if any(keyword in lib_dep_upper for keyword in keywords):
                components.add(component)
        
        return components


class LibraryMapper:
    """Handles mapping between library names and include paths."""
    
    def __init__(self, arduino_framework_dir: str):
        self.arduino_framework_dir = arduino_framework_dir
        self._arduino_libraries_cache = None
    
    def convert_lib_name_to_include(self, lib_name: str) -> str:
        """Convert library name to potential include directory name."""
        # Load Arduino Core Libraries on first call
        if self._arduino_libraries_cache is None:
            self._arduino_libraries_cache = self._get_arduino_core_libraries()
        
        lib_name_lower = lib_name.lower()
        
        # Check Arduino Core Libraries first
        if lib_name_lower in self._arduino_libraries_cache:
            return self._arduino_libraries_cache[lib_name_lower]
        
        # Remove common prefixes and suffixes
        cleaned_name = lib_name_lower
        
        # Remove common prefixes
        prefixes_to_remove = ['lib', 'arduino-', 'esp32-', 'esp-']
        for prefix in prefixes_to_remove:
            if cleaned_name.startswith(prefix):
                cleaned_name = cleaned_name[len(prefix):]
        
        # Remove common suffixes
        suffixes_to_remove = ['-lib', '-library', '.h']
        for suffix in suffixes_to_remove:
            if cleaned_name.endswith(suffix):
                cleaned_name = cleaned_name[:-len(suffix)]
        
        # Check again with cleaned name
        if cleaned_name in self._arduino_libraries_cache:
            return self._arduino_libraries_cache[cleaned_name]
        
        # Direct mapping for common cases not in Arduino libraries
        direct_mapping = {
            'ble': 'bt',
            'bluetooth': 'bt',
            'bluetoothserial': 'bt'
        }
        
        if cleaned_name in direct_mapping:
            return direct_mapping[cleaned_name]
        
        return cleaned_name
    
    def _get_arduino_core_libraries(self) -> Dict[str, str]:
        """Get all Arduino core libraries and their corresponding include paths."""
        libraries_mapping = {}
        
        # Path to Arduino Core Libraries
        arduino_libs_dir = join(self.arduino_framework_dir, "libraries")
        
        if not os.path.exists(arduino_libs_dir):
            return libraries_mapping
        
        try:
            for entry in os.listdir(arduino_libs_dir):
                lib_path = join(arduino_libs_dir, entry)
                if os.path.isdir(lib_path):
                    lib_name = self._get_library_name_from_properties(lib_path)
                    if lib_name:
                        include_path = self._map_library_to_include_path(lib_name, entry)
                        libraries_mapping[lib_name.lower()] = include_path
                        libraries_mapping[entry.lower()] = include_path
        except Exception:
            pass
        
        return libraries_mapping
    
    def _get_library_name_from_properties(self, lib_dir: str) -> Optional[str]:
        """Extract library name from library.properties file."""
        prop_path = join(lib_dir, "library.properties")
        if not os.path.isfile(prop_path):
            return None
        
        try:
            with open(prop_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('name='):
                        return line.split('=', 1)[1].strip()
        except Exception:
            pass
        
        return None
    
    def _map_library_to_include_path(self, lib_name: str, dir_name: str) -> str:
        """Map library name to corresponding include path."""
        lib_name_lower = lib_name.lower().replace(' ', '').replace('-', '_')
        dir_name_lower = dir_name.lower()
        
        # Extended mapping list with Arduino Core Libraries
        extended_mapping = {
            # Core ESP32 mappings
            'wifi': 'esp_wifi',
            'bluetooth': 'bt',
            'bluetoothserial': 'bt',
            'ble': 'bt',
            'bt': 'bt',
            'ethernet': 'esp_eth',
            'websocket': 'esp_websocket_client',
            'http': 'esp_http_client',
            'https': 'esp_https_ota',
            'ota': 'esp_https_ota',
            'spiffs': 'spiffs',
            'fatfs': 'fatfs',
            'mesh': 'esp_wifi_mesh',
            'smartconfig': 'esp_smartconfig',
            'mdns': 'mdns',
            'coap': 'coap',
            'mqtt': 'mqtt',
            'json': 'cjson',
            'mbedtls': 'mbedtls',
            'openssl': 'openssl',
            
            # Arduino Core specific mappings
            'esp32blearduino': 'bt',
            'esp32_ble_arduino': 'bt',
            'esp32': 'esp32',
            'wire': 'driver',
            'spi': 'driver',
            'i2c': 'driver',
            'uart': 'driver',
            'serial': 'driver',
            'analogwrite': 'driver',
            'ledc': 'driver',
            'pwm': 'driver',
            'dac': 'driver',
            'adc': 'driver',
            'touch': 'driver',
            'hall': 'driver',
            'rtc': 'driver',
            'timer': 'esp_timer',
            'preferences': 'arduino_preferences',
            'eeprom': 'arduino_eeprom',
            'update': 'esp_https_ota',
            'httpupdate': 'esp_https_ota',
            'httpclient': 'esp_http_client',
            'httpsclient': 'esp_https_ota',
            'wifimanager': 'esp_wifi',
            'wificlientsecure': 'esp_wifi',
            'wifiserver': 'esp_wifi',
            'wifiudp': 'esp_wifi',
            'wificlient': 'esp_wifi',
            'wifiap': 'esp_wifi',
            'wifimulti': 'esp_wifi',
            'esp32webserver': 'esp_http_server',
            'webserver': 'esp_http_server',
            'asyncwebserver': 'esp_http_server',
            'dnsserver': 'lwip',
            'netbios': 'netbios',
            'simpletime': 'lwip',
            'fs': 'vfs',
            'sd': 'fatfs',
            'sd_mmc': 'fatfs',
            'littlefs': 'esp_littlefs',
            'ffat': 'fatfs',
            'camera': 'esp32_camera',
            'esp_camera': 'esp32_camera',
            'arducam': 'esp32_camera',
            'rainmaker': 'esp_rainmaker',
            'esp_rainmaker': 'esp_rainmaker',
            'provisioning': 'wifi_provisioning',
            'wifiprovisioning': 'wifi_provisioning',
            'espnow': 'esp_now',
            'esp_now': 'esp_now',
            'esptouch': 'esp_smartconfig',
            'ping': 'lwip',
            'netif': 'lwip',
            'tcpip': 'lwip'
        }
        
        # Check extended mapping first
        if lib_name_lower in extended_mapping:
            return extended_mapping[lib_name_lower]
        
        # Check directory name
        if dir_name_lower in extended_mapping:
            return extended_mapping[dir_name_lower]
        
        # Fallback: Use directory name as include path
        return dir_name_lower


class BuildFileManager:
    """Manages backup and restoration of build files."""
    
    def __init__(self, arduino_libs_mcu: str, mcu: str, logger: ComponentLogger):
        self.arduino_libs_mcu = arduino_libs_mcu
        self.mcu = mcu
        self.logger = logger
    
    def backup_pioarduino_build_py(self, env) -> None:
        """Create backup of the original pioarduino-build.py."""
        if "arduino" not in env.subst("$PIOFRAMEWORK"):
            return
        
        build_py_path = join(self.arduino_libs_mcu, "pioarduino-build.py")
        backup_path = join(self.arduino_libs_mcu, f"pioarduino-build.py.{self.mcu}")
        
        if os.path.exists(build_py_path) and not os.path.exists(backup_path):
            shutil.copy2(build_py_path, backup_path)
            self.logger.log_change(f"Created backup of pioarduino-build.py for {self.mcu}")
    
    def restore_pioarduino_build_py(self) -> None:
        """Restore the original pioarduino-build.py from backup."""
        build_py_path = join(self.arduino_libs_mcu, "pioarduino-build.py")
        backup_path = join(self.arduino_libs_mcu, f"pioarduino-build.py.{self.mcu}")
        
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, build_py_path)
            os.remove(backup_path)
            self.logger.log_change("Restored original pioarduino-build.py from backup")
    
    def remove_ignored_lib_includes(self, ignored_libs: Set[str], project_analyzer: ProjectAnalyzer) -> None:
        """Remove include entries for ignored libraries from pioarduino-build.py."""
        build_py_path = join(self.arduino_libs_mcu, "pioarduino-build.py")
        
        if not os.path.exists(build_py_path):
            return
        
        try:
            with open(build_py_path, 'r') as f:
                content = f.read()
            
            original_content = content
            total_removed = 0
            
            # Remove CPPPATH entries for each ignored library
            for lib_name in ignored_libs:
                # Universal protection: Skip if component is actually used in project
                if project_analyzer.is_component_used_in_project(lib_name):
                    self.logger.log_change(f"Skipping removal of library '{lib_name}' - detected as used in project")
                    continue
                    
                # Multiple patterns to catch different include formats
                patterns = [
                    rf'.*join\([^,]*,\s*"include",\s*"{re.escape(lib_name)}"[^)]*\),?\n',
                    rf'.*"include/{re.escape(lib_name)}"[^,\n]*,?\n',
                    rf'.*"[^"]*include[^"]*{re.escape(lib_name)}[^"]*"[^,\n]*,?\n',
                    rf'.*"[^"]*/{re.escape(lib_name)}/include[^"]*"[^,\n]*,?\n',
                    rf'.*"[^"]*{re.escape(lib_name)}[^"]*include[^"]*"[^,\n]*,?\n',
                    rf'.*join\([^)]*"include"[^)]*"{re.escape(lib_name)}"[^)]*\),?\n',
                    rf'.*"{re.escape(lib_name)}/include"[^,\n]*,?\n',
                    rf'\s*"[^"]*/{re.escape(lib_name)}/[^"]*",?\n'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        content = re.sub(pattern, '', content)
                        total_removed += len(matches)
                        self.logger.log_change(f"Removed {len(matches)} include entries for library '{lib_name}'")
            
            # Clean up empty lines and trailing commas
            content = re.sub(r'\n\s*\n', '\n', content)
            content = re.sub(r',\s*\n\s*\]', '\n]', content)
            
            # Validate and write changes
            if self._validate_changes(original_content, content) and content != original_content:
                with open(build_py_path, 'w') as f:
                    f.write(content)
                self.logger.log_change(f"Successfully updated build file with {total_removed} total removals")
                
        except Exception as e:
            self.logger.log_change(f"Error processing ignored library includes: {str(e)}")
    
    def remove_cpppath_entries(self, removed_components: Set[str]) -> None:
        """Remove CPPPATH entries for removed components from pioarduino-build.py."""
        build_py_path = join(self.arduino_libs_mcu, "pioarduino-build.py")
        
        if not os.path.exists(build_py_path):
            return
        
        try:
            with open(build_py_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Remove CPPPATH entries for each removed component
            for component in removed_components:
                patterns = [
                    rf'.*join\([^,]*,\s*"include",\s*"{re.escape(component)}"[^)]*\),?\n',
                    rf'.*"include/{re.escape(component)}"[^,\n]*,?\n',
                    rf'.*"[^"]*include[^"]*{re.escape(component)}[^"]*"[^,\n]*,?\n'
                ]
                
                for pattern in patterns:
                    content = re.sub(pattern, '', content)
            
            if content != original_content:
                with open(build_py_path, 'w') as f:
                    f.write(content)
                self.logger.log_change(f"Cleaned up CPPPATH entries for removed components")
                
        except Exception as e:
            self.logger.log_change(f"Error cleaning up CPPPATH entries: {str(e)}")
    
    def _validate_changes(self, original_content: str, new_content: str) -> bool:
        """Validate that the changes are reasonable."""
        original_lines = len(original_content.splitlines())
        new_lines = len(new_content.splitlines())
        removed_lines = original_lines - new_lines
        
        # Don't allow removing more than 50% of the file or negative changes
        return not (removed_lines > original_lines * 0.5 or removed_lines < 0)


class ComponentManager:
    """Manages IDF components for ESP32 Arduino framework builds with logging support."""
    
    def __init__(self, env):
        """Initialize the ComponentManager with all required dependencies."""
        self.env = env
        self.platform = env.PioPlatform()
        self.config = env.GetProjectConfig()
        self.board = env.BoardConfig()
        self.mcu = self.board.get("build.mcu", "esp32").lower()
        self.project_src_dir = env.subst("$PROJECT_SRC_DIR")
        self.arduino_framework_dir = self.platform.get_package_dir("framework-arduinoespressif32")
        self.arduino_libs_mcu = join(self.platform.get_package_dir("framework-arduinoespressif32-libs"), self.mcu)
        
        # Component tracking
        self.removed_components: Set[str] = set()
        self.ignored_libs: Set[str] = set()
        
        # Initialize helper classes
        self.logger = ComponentLogger()
        self.yaml_handler = ComponentYamlHandler(self.logger)
        self.project_analyzer = ProjectAnalyzer(env)
        self.library_mapper = LibraryMapper(self.arduino_framework_dir)
        self.build_file_manager = BuildFileManager(self.arduino_libs_mcu, self.mcu, self.logger)
    
    def _log_change(self, message: str) -> None:
        """Delegate to logger for backward compatibility."""
        self.logger.log_change(message)

    def handle_component_settings(self, add_components: bool = False, remove_components: bool = False) -> None:
        """Handle adding and removing IDF components based on project configuration."""
        # Create backup before first component removal and always when a component is added
        if remove_components and not self.removed_components or add_components:
            self.build_file_manager.backup_pioarduino_build_py(self.env)
            self._log_change("Created backup of build file")
    
        # Check if env and GetProjectOption are available
        if hasattr(self, 'env') and hasattr(self.env, 'GetProjectOption'):
            component_yml_path = self.yaml_handler.get_or_create_component_yml(
                self.arduino_framework_dir, self.project_src_dir)
            component_data = self.yaml_handler.load_component_yml(component_yml_path)
    
            if remove_components:
                try:
                    remove_option = self.env.GetProjectOption("custom_component_remove", None)
                    if remove_option:
                        components_to_remove = remove_option.splitlines()
                        self._remove_components(component_data, components_to_remove)
                except Exception as e:
                    self._log_change(f"Error removing components: {str(e)}")
    
            if add_components:
                try:
                    add_option = self.env.GetProjectOption("custom_component_add", None)
                    if add_option:
                        components_to_add = add_option.splitlines()
                        self._add_components(component_data, components_to_add)
                except Exception as e:
                    self._log_change(f"Error adding components: {str(e)}")

            self.yaml_handler.save_component_yml(component_yml_path, component_data)
        
            # Clean up removed components
            if self.removed_components:
                self._cleanup_removed_components()

        self.handle_lib_ignore()
        
        # Print summary
        if self.logger.get_change_count() > 0:
            self._log_change(f"Session completed with {self.logger.get_change_count()} changes")
    
    def handle_lib_ignore(self) -> None:
        """Handle lib_ignore entries from platformio.ini and remove corresponding includes."""
        # Create backup before processing lib_ignore
        if not self.ignored_libs:
            self.build_file_manager.backup_pioarduino_build_py(self.env)
        
        # Get lib_ignore entries from current environment only
        lib_ignore_entries = self._get_lib_ignore_entries()
        
        if lib_ignore_entries:
            self.ignored_libs.update(lib_ignore_entries)
            self.build_file_manager.remove_ignored_lib_includes(self.ignored_libs, self.project_analyzer)
            self._log_change(f"Processed {len(lib_ignore_entries)} ignored libraries")
    
    def restore_pioarduino_build_py(self, source=None, target=None, env=None) -> None:
        """Restore the original pioarduino-build.py from backup."""
        self.build_file_manager.restore_pioarduino_build_py()
    
    def _get_lib_ignore_entries(self) -> List[str]:
        """Get lib_ignore entries from current environment configuration only."""
        try:
            # Get lib_ignore from current environment only
            lib_ignore = self.env.GetProjectOption("lib_ignore", [])
            
            if isinstance(lib_ignore, str):
                lib_ignore = [lib_ignore]
            elif lib_ignore is None:
                lib_ignore = []
            
            # Clean and normalize entries
            cleaned_entries = []
            for entry in lib_ignore:
                entry = str(entry).strip()
                if entry:
                    # Convert library names to potential include directory names
                    include_name = self.library_mapper.convert_lib_name_to_include(entry)
                    cleaned_entries.append(include_name)
            
            # Filter out critical ESP32 components that should never be ignored
            critical_components = [
                'lwip', 'freertos', 'esp_system', 'esp_common', 'driver',
                'nvs_flash', 'spi_flash', 'esp_timer', 'esp_event', 'log'
            ]
            
            filtered_entries = []
            for entry in cleaned_entries:
                if entry not in critical_components:
                    filtered_entries.append(entry)
            
            return filtered_entries
            
        except Exception:
            return []
    
    def _remove_components(self, component_data: Dict[str, Any], components_to_remove: list) -> None:
        """Remove specified components from the configuration."""
        dependencies = component_data.setdefault("dependencies", {})
        
        for component in components_to_remove:
            component = component.strip()
            if not component:
                continue
                
            if component in dependencies:
                del dependencies[component]
                self._log_change(f"Removed component: {component}")
                
                # Track for cleanup
                filesystem_name = self._convert_component_name_to_filesystem(component)
                self.removed_components.add(filesystem_name)
    
    def _add_components(self, component_data: Dict[str, Any], components_to_add: list) -> None:
        """Add specified components to the configuration."""
        dependencies = component_data.setdefault("dependencies", {})
        
        for component in components_to_add:
            component = component.strip()
            if len(component) <= 4:  # Skip too short entries
                continue
            
            component_name, version = self._parse_component_entry(component)
            
            if component_name not in dependencies:
                dependencies[component_name] = {"version": version}
                self._log_change(f"Added component: {component_name} (version: {version})")
    
    def _parse_component_entry(self, entry: str) -> tuple[str, str]:
        """Parse component entry into name and version."""
        if "@" in entry:
            name, version = entry.split("@", 1)
            return (name.strip(), version.strip())
        return (entry.strip(), "*")
    
    def _convert_component_name_to_filesystem(self, component_name: str) -> str:
        """Convert component name from registry format to filesystem format."""
        return component_name.replace("/", "__")
    
    def _cleanup_removed_components(self) -> None:
        """Clean up removed components and restore original build file."""
        for component in self.removed_components:
            self._remove_include_directory(component)
        
        self.build_file_manager.remove_cpppath_entries(self.removed_components)
    
    def _remove_include_directory(self, component: str) -> None:
        """Remove include directory for a component."""
        include_path = join(self.arduino_libs_mcu, "include", component)
        
        if os.path.exists(include_path):
            shutil.rmtree(include_path)
            self._log_change(f"Removed include directory: {include_path}")
