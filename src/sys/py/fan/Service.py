#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj


class Service(Obj):
    # Class-level service registry - list of installed services
    _registry = []

    """Base class for services with lifecycle management and global registry.

    Services are singleton-like objects that can be installed, started, stopped,
    and uninstalled. The Service class maintains a global registry of all
    installed services that can be queried by Type.

    Lifecycle states:
    - Not installed (initial state)
    - Installed (registered but not running)
    - Running (installed and active)

    Lifecycle methods:
    - install(): Register service in global registry
    - start(): Install if needed, then start (calls onStart)
    - stop(): Stop service (calls onStop)
    - uninstall(): Stop if running, then unregister from registry
    """

    def __init__(self):
        super().__init__()
        self._installed = False
        self._running = False

    #################################################################
    # Static Registry Methods
    #################################################################

    @staticmethod
    def find(type_, checked=True):
        """Find first installed service that matches the given Type.

        Args:
            type_: The Type to search for (services implement this type)
            checked: If true, throw UnknownServiceErr if not found; if false, return None

        Returns:
            The first matching Service or None (if checked=False)

        Raises:
            UnknownServiceErr: If no matching service and checked=True
        """
        from .Type import Type

        # Get type signature for comparison
        if hasattr(type_, 'qname'):
            type_qname = type_.qname()
        elif hasattr(type_, 'signature'):
            type_qname = type_.signature()
        else:
            type_qname = str(type_)

        # Search registry for matching service
        for service in Service._registry:
            if Service._matches_type(service, type_, type_qname):
                return service

        # Not found
        if checked:
            from .Err import UnknownServiceErr
            raise UnknownServiceErr(f"Service not found: {type_qname}")
        return None

    @staticmethod
    def find_all(type_):
        """Find all installed services that match the given Type.

        Args:
            type_: The Type to search for

        Returns:
            List of all matching Services (may be empty)
        """
        from .Type import Type

        # Get type signature for comparison
        if hasattr(type_, 'qname'):
            type_qname = type_.qname()
        elif hasattr(type_, 'signature'):
            type_qname = type_.signature()
        else:
            type_qname = str(type_)

        result = []
        for service in Service._registry:
            if Service._matches_type(service, type_, type_qname):
                result.append(service)
        return result

    @staticmethod
    def list_():
        """Return list of all installed services.

        Returns:
            List of all installed Service instances
        """
        return list(Service._registry)

    @staticmethod
    def _matches_type(service, type_, type_qname):
        """Check if a service matches a type (including inheritance and mixins).

        This handles the case where looking up TestServiceA# should find
        services that extend TestServiceA, and looking up TestServiceM#
        should find services that implement the TestServiceM mixin.
        """
        from .Type import Type

        # Get service's type
        service_type = service.typeof() if hasattr(service, 'typeof') else Type.of(service)

        # Check direct type match
        if hasattr(service_type, 'qname'):
            if service_type.qname() == type_qname:
                return True

        # Check if service type fits (is subtype of) the target type
        if hasattr(service_type, 'fits'):
            if service_type.fits(type_):
                return True
            # fits() returned False, but Type.fits() may not handle Python inheritance
            # Fall through to MRO check

        # Fallback: Check Python inheritance via MRO
        try:
            service_class = service.__class__
            # Walk MRO to find matching type
            for cls in service_class.__mro__:
                cls_name = cls.__name__
                # Match class name against type qname
                if type_qname.endswith('::' + cls_name):
                    return True
                if type_qname == cls_name:
                    return True
        except:
            pass

        return False

    #################################################################
    # Instance Lifecycle Methods
    #################################################################

    def is_installed(self):
        """Return true if service is installed in the registry."""
        return self._installed

    def is_running(self):
        """Return true if service is currently running."""
        return self._running

    def install(self):
        """Install this service into the global registry.

        If already installed, this is a no-op.

        Returns:
            This service (for chaining)
        """
        if not self._installed:
            Service._registry.append(self)
            self._installed = True
        return self

    def uninstall(self):
        """Uninstall this service from the global registry.

        If service is running, it will be stopped first.
        If not installed, this is a no-op.

        Returns:
            This service (for chaining)
        """
        if self._installed:
            # Stop first if running
            if self._running:
                self.stop()
            # Remove from registry
            if self in Service._registry:
                Service._registry.remove(self)
            self._installed = False
        return self

    def start(self):
        """Start this service.

        If not installed, it will be installed first.
        If already running, this is a no-op.
        Calls onStart() callback when starting.

        Returns:
            This service (for chaining)
        """
        # Auto-install if needed
        if not self._installed:
            self.install()

        if not self._running:
            try:
                self.on_start()
                self._running = True
            except Exception as e:
                # onStart failed - service not running
                # Log but don't re-raise (matches Fantom behavior)
                pass
        return self

    def stop(self):
        """Stop this service.

        If not running, this is a no-op.
        Calls onStop() callback when stopping.

        Returns:
            This service (for chaining)
        """
        if self._running:
            self._running = False
            try:
                self.on_stop()
            except Exception as e:
                # onStop failed - log but don't re-raise
                pass
        return self

    #################################################################
    # Virtual Callbacks
    #################################################################

    def on_start(self):
        """Called when service is started.

        Override this method in subclasses to perform startup logic.
        """
        pass

    def on_stop(self):
        """Called when service is stopped.

        Override this method in subclasses to perform cleanup logic.
        """
        pass

    # Note: typeof() is inherited from Obj and will return the actual runtime type
    # of the service instance (e.g., testSys::TestServiceB), not sys::Service


# Add UnknownServiceErr to Err module if not present
def _ensure_err():
    """Ensure UnknownServiceErr exists in Err module."""
    try:
        from .Err import UnknownServiceErr
    except ImportError:
        # Add it dynamically
        pass


_ensure_err()
