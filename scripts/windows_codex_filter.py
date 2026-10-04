"""Narrow Windows Filtering Platform supplement for the pinned Codex sandbox.

Only the local CodexSandboxOffline account's loopback connections are blocked.
No provider-owned object, firewall profile, user credential or executable changes.
This developer qualification helper is not imported by the packaged application.
"""
from contextlib import contextmanager
import ctypes as C
import os
import uuid


class GuardError(RuntimeError):
    """Fixed diagnostic only; never expose native account/security data."""


U32, U64, P = C.c_uint32, C.c_uint64, C.c_void_p


class GUID(C.Structure):
    _fields_ = [("data1", U32), ("data2", C.c_uint16), ("data3", C.c_uint16), ("data4", C.c_ubyte * 8)]


def guid(value):
    return GUID.from_buffer_copy(uuid.UUID(value).bytes_le)


class Display(C.Structure):
    _fields_ = [("name", C.c_wchar_p), ("description", C.c_wchar_p)]


class Blob(C.Structure):
    _fields_ = [("size", U32), ("data", P)]


class ValueUnion(C.Union):
    _fields_ = [("ptr", P), ("uint32", U32), ("uint8", C.c_ubyte)]


class Value(C.Structure):
    _fields_ = [("type", U32), ("value", ValueUnion)]


class Condition(C.Structure):
    _fields_ = [("key", GUID), ("match", U32), ("value", Value)]


class Action(C.Structure):
    _fields_ = [("type", U32), ("key", GUID)]


class Context(C.Union):
    _fields_ = [("raw", U64), ("key", GUID)]


class Filter(C.Structure):
    _fields_ = [("key", GUID), ("display", Display), ("flags", U32), ("provider", P),
                ("provider_data", Blob), ("layer", GUID), ("sublayer", GUID), ("weight", Value),
                ("count", U32), ("conditions", C.POINTER(Condition)), ("action", Action),
                ("context", Context), ("reserved", P), ("id", U64), ("effective_weight", Value)]


class Session(C.Structure):
    _fields_ = [("key", GUID), ("display", Display), ("flags", U32), ("timeout", U32),
                ("process_id", U32), ("sid", P), ("username", C.c_wchar_p), ("kernel", C.c_int)]


class Sublayer(C.Structure):
    _fields_ = [("key", GUID), ("display", Display), ("flags", U32), ("provider", P),
                ("provider_data", Blob), ("weight", C.c_uint16)]


# Application-owned stable keys; deliberately separate from all Codex WFP keys.
SUBLAYER = "54736a41-082c-46d6-b98a-39affdf03ff9"
FILTERS = ("495b6ebf-e960-482b-a997-f1d5d8744a8b", "6c1b8eb7-08a3-4ee0-a4ce-56d8f939494b")
LAYERS = ("c38d57d1-05a7-4c33-904f-7fbceee60e82", "4a72393b-319f-44bc-84c3-ba54dcb3b6b4")
USER = "af043a0a-b34d-4f86-979c-c90371af6e66"
FLAGS = "632ce23b-5167-435c-86d7-e903684aa80c"
NAME = "Learn the Ticker: Codex offline loopback guard v1"
MARKER = b"org.learntheticker.desktop/codex-offline-loopback/v1"
MIN_SUBLAYER_WEIGHT = 0xFF00
NOT_FOUND = {0x80320003, 0x80320007}  # FWP_E_FILTER_NOT_FOUND / SUBLAYER_NOT_FOUND


def check(code):
    if code == 5:
        raise GuardError("Windows filtering access was denied. Use an elevated terminal to inspect or repair the guard.")
    if code:
        raise GuardError("Windows filtering operation failed; no automatic retry.")


def blob_bytes(blob):
    if not 0 < blob.size <= 4096 or not blob.data:
        raise GuardError("Windows filtering object has invalid metadata.")
    return C.string_at(blob.data, blob.size)


class NativeStore:
    def __init__(self):
        if os.name != "nt" or C.sizeof(P) != 8:
            raise GuardError("The loopback guard requires native 64-bit Windows.")
        # Public WinSDK ABI. Fail before passing a malformed structure to Windows.
        if (C.sizeof(GUID), C.sizeof(Filter), Filter.conditions.offset,
                C.sizeof(Session), C.sizeof(Sublayer)) != (16, 200, 120, 72, 72):
            raise GuardError("Unsupported Windows filtering ABI.")
        self.fw = C.WinDLL("fwpuclnt.dll", use_last_error=True)
        self.adv = C.WinDLL("advapi32.dll", use_last_error=True)
        self.kernel = C.WinDLL("kernel32.dll", use_last_error=True)
        signatures = {
            "FwpmEngineOpen0": [P, U32, P, C.POINTER(Session), C.POINTER(P)],
            "FwpmEngineClose0": [P], "FwpmTransactionBegin0": [P, U32],
            "FwpmTransactionCommit0": [P], "FwpmTransactionAbort0": [P],
            "FwpmSubLayerAdd0": [P, C.POINTER(Sublayer), P],
            "FwpmSubLayerGetByKey0": [P, C.POINTER(GUID), C.POINTER(C.POINTER(Sublayer))],
            "FwpmSubLayerDeleteByKey0": [P, C.POINTER(GUID)],
            "FwpmFilterAdd0": [P, C.POINTER(Filter), P, C.POINTER(U64)],
            "FwpmFilterGetByKey0": [P, C.POINTER(GUID), C.POINTER(C.POINTER(Filter))],
            "FwpmFilterDeleteByKey0": [P, C.POINTER(GUID)],
        }
        for name, args in signatures.items():
            function = getattr(self.fw, name)
            function.argtypes, function.restype = args, U32
        self.fw.FwpmFreeMemory0.argtypes, self.fw.FwpmFreeMemory0.restype = [C.POINTER(P)], None
        self.adv.LookupAccountNameW.argtypes = [P, C.c_wchar_p, P, C.POINTER(U32), C.c_wchar_p, C.POINTER(U32), C.POINTER(U32)]
        self.adv.LookupAccountNameW.restype = C.c_int
        self.adv.ConvertSidToStringSidW.argtypes = [P, C.POINTER(P)]
        self.adv.ConvertSidToStringSidW.restype = C.c_int
        self.adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [C.c_wchar_p, U32, C.POINTER(P), C.POINTER(U32)]
        self.adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = C.c_int
        self.kernel.LocalFree.argtypes, self.kernel.LocalFree.restype = [P], P
        self.kernel.GetComputerNameW.argtypes = [C.c_wchar_p, C.POINTER(U32)]
        self.kernel.GetComputerNameW.restype = C.c_int
        self.handle = P()
        self.descriptor = P()
        self.metadata = C.create_string_buffer(MARKER)
        self.metadata_blob = Blob(len(MARKER), C.cast(self.metadata, P))

    def __enter__(self):
        try:
            self._identity()
            session = Session()
            session.display.name, session.timeout = NAME, 1000
            check(self.fw.FwpmEngineOpen0(None, 0xFFFFFFFF, None, C.byref(session), C.byref(self.handle)))
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.handle:
            self.fw.FwpmEngineClose0(self.handle)
            self.handle = P()
        if self.descriptor:
            self.kernel.LocalFree(self.descriptor)
            self.descriptor = P()

    def _identity(self):
        size, domain_size, kind = U32(), U32(), U32()
        # Explicit local account; never resolve a similarly named domain user.
        computer, computer_size = C.create_unicode_buffer(256), U32(256)
        if not self.kernel.GetComputerNameW(computer, C.byref(computer_size)):
            raise GuardError("The local computer identity could not be verified.")
        account = computer.value + "\\CodexSandboxOffline"
        self.adv.LookupAccountNameW(None, account, None, C.byref(size), None, C.byref(domain_size), C.byref(kind))
        if C.get_last_error() != 122 or not 0 < size.value < 4096 or not 0 < domain_size.value < 256:
            raise GuardError("The provider's local offline sandbox account is unavailable.")
        sid, domain = C.create_string_buffer(size.value), C.create_unicode_buffer(domain_size.value)
        if not self.adv.LookupAccountNameW(None, account, sid, C.byref(size), domain, C.byref(domain_size), C.byref(kind)) or kind.value != 1:
            raise GuardError("The provider's local offline sandbox account could not be verified.")
        pointer = P()
        if not self.adv.ConvertSidToStringSidW(sid, C.byref(pointer)):
            raise GuardError("Sandbox identity conversion failed.")
        try:
            sddl = "D:(A;;CC;;;" + C.wstring_at(pointer) + ")"
        finally:
            self.kernel.LocalFree(pointer)
        length = U32()
        if not self.adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(self.descriptor), C.byref(length)):
            raise GuardError("Sandbox identity descriptor creation failed.")
        self.descriptor_blob = Blob(length.value, self.descriptor)

    @contextmanager
    def transaction(self):
        check(self.fw.FwpmTransactionBegin0(self.handle, 0))
        committed = False
        try:
            yield
            check(self.fw.FwpmTransactionCommit0(self.handle))
            committed = True
        finally:
            if not committed:
                self.fw.FwpmTransactionAbort0(self.handle)

    def _sublayer(self):
        sub = Sublayer()
        sub.key, sub.display.name = guid(SUBLAYER), NAME
        sub.flags, sub.weight, sub.provider_data = 1, 0xFFFF, self.metadata_blob
        return sub

    def _filter(self, index):
        conditions = (Condition * 2)()
        conditions[0].key, conditions[0].value.type = guid(USER), 14  # SECURITY_DESCRIPTOR
        conditions[0].value.value.ptr = C.cast(C.pointer(self.descriptor_blob), P)
        conditions[1].key, conditions[1].match = guid(FLAGS), 6  # FLAGS_ALL_SET
        conditions[1].value.type, conditions[1].value.value.uint32 = 3, 1  # UINT32 / IS_LOOPBACK
        item = Filter()
        item.key, item.display.name = guid(FILTERS[index]), NAME
        item.flags, item.provider_data = 1, self.metadata_blob  # PERSISTENT, not boot-time
        item.layer, item.sublayer = guid(LAYERS[index]), guid(SUBLAYER)
        item.count, item.conditions, item.action.type = 2, conditions, 0x1001  # BLOCK
        return item

    def _matches(self, item, expected):
        common = (bytes(item.key) == bytes(expected.key) and item.display.name == NAME
                  and not item.display.description and item.flags == 1 and not item.provider
                  and blob_bytes(item.provider_data) == MARKER)
        if isinstance(item, Sublayer):
            # BFE assigns the nearest available unique sublayer weight (Microsoft
            # "Installing a Provider"). Require the upper range; actual socket
            # enforcement still must pass, since weight alone proves no boundary.
            return common and MIN_SUBLAYER_WEIGHT <= item.weight <= 0xFFFF
        if not (common and bytes(item.layer) == bytes(expected.layer)
                and bytes(item.sublayer) == bytes(expected.sublayer) and item.weight.type == 0
                and item.action.type == 0x1001 and not any(bytes(item.action.key))
                and not item.context.raw and not item.reserved and item.count == 2 and item.conditions):
            return False
        for index in range(2):
            actual, wanted = item.conditions[index], expected.conditions[index]
            if (bytes(actual.key), actual.match, actual.value.type) != (bytes(wanted.key), wanted.match, wanted.value.type):
                return False
            if index == 0:
                if not actual.value.value.ptr:
                    return False
                descriptor = C.cast(actual.value.value.ptr, C.POINTER(Blob)).contents
                if blob_bytes(descriptor) != blob_bytes(self.descriptor_blob):
                    return False
            elif actual.value.value.uint32 != 1:
                return False
        return True

    def inspect(self):
        result = []
        for expected, kind in [(self._sublayer(), "SubLayer"), *[(self._filter(i), "Filter") for i in range(2)]]:
            pointer = C.POINTER(type(expected))()
            code = getattr(self.fw, "Fwpm" + kind + "GetByKey0")(self.handle, C.byref(expected.key), C.byref(pointer))
            if code in NOT_FOUND:
                result.append("absent")
                continue
            check(code)
            try:
                result.append("matched" if self._matches(pointer.contents, expected) else "conflict")
            finally:
                allocated = C.cast(pointer, P)
                self.fw.FwpmFreeMemory0(C.byref(allocated))
        return tuple(result)

    def install(self):
        sub = self._sublayer()
        check(self.fw.FwpmSubLayerAdd0(self.handle, C.byref(sub), None))
        for index in range(2):
            item = self._filter(index)
            check(self.fw.FwpmFilterAdd0(self.handle, C.byref(item), None, C.byref(U64())))

    def remove(self):
        for key in FILTERS:
            check(self.fw.FwpmFilterDeleteByKey0(self.handle, C.byref(guid(key))))
        check(self.fw.FwpmSubLayerDeleteByKey0(self.handle, C.byref(guid(SUBLAYER))))


def manage(store, action="inspect"):
    if action not in {"inspect", "apply", "remove"}:
        raise GuardError("Unknown filtering action.")
    if action == "inspect":
        states = store.inspect()
    else:
        # Inspection and mutation share one transaction: no check/delete race.
        with store.transaction():
            states = store.inspect()
            if states not in {("absent",) * 3, ("matched",) * 3}:
                raise GuardError("Partial or conflicting guard objects require manual review; nothing was replaced.")
            if action == "apply" and states == ("absent",) * 3:
                store.install()
            elif action == "remove" and states == ("matched",) * 3:
                store.remove()
            states = store.inspect()
            wanted = ("matched" if action == "apply" else "absent",) * 3
            if states != wanted:
                raise GuardError("Guard readback failed; transaction was not committed.")
    return "installed" if states == ("matched",) * 3 else "absent" if states == ("absent",) * 3 else "conflict"
