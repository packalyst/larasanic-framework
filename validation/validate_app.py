import sys
from larasanic.support.config_validator import validate_all_configs, ConfigValidationError

class ValidateApp:
    _validated: bool = False

    @classmethod
    def validate_startup_app(cls):
        if not cls._validated:
            # Validate configuration before starting (fail fast on config errors)
            try:
                validators = validate_all_configs()
                # Display warnings if any
                has_warnings = False
                for config_name, validator in validators.items():
                    warnings = validator.get_warnings()
                    if warnings:
                        if not has_warnings:
                            print("\n⚠  Configuration warnings:")
                            has_warnings = True
                        for warning in warnings:
                            print(f"   [{config_name}] {warning}")

                if has_warnings:
                    print()  # Add blank line after warnings

            except ConfigValidationError as e:
                print("\n" + "=" * 70)
                print("✗ CONFIGURATION VALIDATION FAILED")
                print("=" * 70)
                print(str(e))
                print("\nPlease fix the configuration errors before starting the application.")
                print("=" * 70)
                sys.exit(1)

ValidateApp.validate_startup_app()
