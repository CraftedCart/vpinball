// Win32++   Version 8.9.1
// Release Date: 10th September 2021
//
//      David Nash
//      email: dnash@bigpond.net.au
//      url: https://sourceforge.net/projects/win32-framework
//
//
// Copyright (c) 2005-2021  David Nash
//
// Permission is hereby granted, free of charge, to
// any person obtaining a copy of this software and
// associated documentation files (the "Software"),
// to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify,
// merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom
// the Software is furnished to do so, subject to the
// following conditions:
//
// The above copyright notice and this permission notice
// shall be included in all copies or substantial portions
// of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF
// ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
// TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
// PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
// SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR
// ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
// ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
// OR OTHER DEALINGS IN THE SOFTWARE.
//
////////////////////////////////////////////////////////



#ifndef _WIN32XX_APPCORE0_H_
#define _WIN32XX_APPCORE0_H_


///////////////////////////////////////////////////////
// wxx_appcore0.h
// This file contains the declarations of the following set of classes.
//
// 1) CCriticalSection: This class is used internally to manage thread access
//            to shared resources. You can also use this class to lock and
//            release your own critical sections.
//
// 2) CObject: A base class for CWnd and any other class that uses serialization.
//             It provides a virtual Serialize function for use by CArchive.
//
// 3) CThreadLock: Provides a RAII-style wrapper for CCriticalSection.
//
// 4) CHGlobal:  A class which wraps a global memory handle. The memory is
//               automatically freed when the CHGlobal object goes out of scope.
//
// 5) CWinThread: This class is the parent class for CWinApp. It is also the
//            class used to create additional GUI and worker threads.
//
// 6) CWinApp: This class is used start Win32++ and run the message loop. You
//            should inherit from this class to start Win32++ in your own
//            application.



//////////////////////////////////////
//  Include the C++ and windows header files
//

// Specify minimum acceptable version macros
// These are suitable for Windows 95 and Windows NT
#ifndef WINVER
  #define WINVER            0x0400
#endif
#ifndef _WIN32_WINDOWS
  #define _WIN32_WINDOWS    WINVER
#endif
#ifndef _WIN32_IE
 #define _WIN32_IE          WINVER
#endif


// Remove pointless warning messages
#ifdef _MSC_VER
  #if _MSC_VER < 1310    // before VS2003
    #pragma warning (disable : 4511) // copy operator could not be generated
    #pragma warning (disable : 4512) // assignment operator could not be generated
    #pragma warning (disable : 4702) // unreachable code (bugs in Microsoft's STL)
    #pragma warning (disable : 4786) // identifier was truncated
  #endif
#endif

#ifdef __BORLANDC__
  #pragma option -w-8026            // functions with exception specifications are not expanded inline
  #pragma option -w-8027            // function not expanded inline
  #pragma option -w-8030            // Temporary used for 'rhs'
  #pragma option -w-8004            // Assigned value is never used
  #define STRICT 1
#endif


#define _WINSOCK_DEPRECATED_NO_WARNINGS

#include <cassert>
#include <vector>
#include <algorithm>
#include <string>
#include <map>
#include <WinSock2.h>
#include <Windows.h>
#include <CommCtrl.h>
#include <stdio.h>
#include <stdarg.h>
#include <tchar.h>
#ifndef _WIN32_WCE
  #include <Shlwapi.h>
  #include <process.h>
  #include <sstream>
#endif

#ifdef _WIN32_WCE
  #include "wxx_wcestddef.h"
#endif

#include "wxx_shared_ptr.h"

// Required for WinCE
#ifndef TLS_OUT_OF_INDEXES
  #define TLS_OUT_OF_INDEXES (static_cast<DWORD_PTR>(-1))
#endif
#ifndef WM_PARENTNOTIFY
  #define WM_PARENTNOTIFY 0x0210
#endif


// For compilers lacking Win64 support
#ifndef  GetWindowLongPtr
  #define GetWindowLongPtr   GetWindowLong
  #define SetWindowLongPtr   SetWindowLong
  #define GWLP_WNDPROC       GWL_WNDPROC
  #define GWLP_HINSTANCE     GWL_HINSTANCE
  #define GWLP_ID            GWL_ID
  #define GWLP_USERDATA      GWL_USERDATA
  #define DWLP_DLGPROC       DWL_DLGPROC
  #define DWLP_MSGRESULT     DWL_MSGRESULT
  #define DWLP_USER          DWL_USER
  #define DWORD_PTR          DWORD
  #define LONG_PTR           LONG
  #define ULONG_PTR          LONG
#endif
#ifndef GetClassLongPtr
  #define GetClassLongPtr    GetClassLong
  #define SetClassLongPtr    SetClassLong
  #define GCLP_HBRBACKGROUND GCL_HBRBACKGROUND
  #define GCLP_HCURSOR       GCL_HCURSOR
  #define GCLP_HICON         GCL_HICON
  #define GCLP_HICONSM       GCL_HICONSM
  #define GCLP_HMODULE       GCL_HMODULE
  #define GCLP_MENUNAME      GCL_MENUNAME
  #define GCLP_WNDPROC       GCL_WNDPROC
#endif


// Automatically include the Win32xx namespace
// define NO_USING_NAMESPACE to skip this step
namespace Win32xx {}
#ifndef NO_USING_NAMESPACE
using namespace Win32xx;
#endif


// Ensure UNICODE and _UNICODE definitions are consistent
#ifdef _UNICODE
  #ifndef UNICODE
    #define UNICODE
  #endif
#endif

#ifdef UNICODE
  #ifndef _UNICODE
    #define _UNICODE
  #endif
#endif

// Define our own MIN and MAX macros
// This avoids inconsistencies with MinGW and other compilers, and
// avoids conflicts between typical min/max macros and std::min/std::max
#define MAX(a,b)        (((a) > (b)) ? (a) : (b))
#define MIN(a,b)        (((a) < (b)) ? (a) : (b))

// Version macro
#define _WIN32XX_VER 0x0891     // Win32++ version 8.9.1

// Define the TRACE Macro
// In debug mode, TRACE send text to the debug/output pane, or an external debugger
// In release mode, TRACE is ignored.
#ifndef TRACE
  #ifdef NDEBUG
    #define TRACE(str) (void(0))
  #else
    #define TRACE(str) Trace(str)
  #endif
#endif

// Define the VERIFY macro
// In debug mode, VERIFY asserts if the expression evaluates to zero
// In release mode, VERIFY evaluates the expression, but doesn't assert.
#ifndef VERIFY
  #ifdef NDEBUG
    #define VERIFY(f) ((void)(f))
  #else
    #define VERIFY(f) assert(f)
  #endif
#endif

#include "wxx_cstring.h"

namespace Win32xx
{

    ////////////////////////////////////////////////
    // Forward declarations.
    //  These classes are defined later or elsewhere
    class CArchive;
    class CBitmap;
    class CBrush;
    class CClientDC;
    class CClientDCEx;
    class CDataExchange;
    class CDC;
    class CDocker;
    class CFont;
    class CGDIObject;
    class CImageList;
    class CMDIChild;
    class CMemDC;
    class CMenu;
    class CMenuBar;
    class CPaintDC;
    class CPalette;
    class CPen;
    class CPropertyPage;
    class CRgn;
    class CWinApp;
    class CWinThread;
    class CWindowDC;
    class CWnd;
    struct CDC_Data;
    struct MenuItemData;
    struct TLSData;

    // tString is a TCHAR std::string
    typedef std::basic_string<TCHAR> tString;
  #ifndef _WIN32_WCE
    typedef std::basic_stringstream<TCHAR> tStringStream;
  #endif

    // Some useful smart pointers
    // Note: Modern C++ compilers can use these typedefs instead.
    // typedef std::shared_ptr<CBitmap> BitmapPtr;
    // typedef std::shared_ptr<CBrush> BrushPtr;
    // typedef std::shared_ptr<CDC> DCPtr;
    // typedef std::shared_ptr<CDocker> DockPtr;
    // typedef std::shared_ptr<CFont> FontPtr;
    // typedef std::shared_ptr<CGDIObject> GDIPtr;
    // typedef std::shared_ptr<CImageList> ImageListPtr;
    // typedef std::shared_ptr<CMDIChild> MDIChildPtr;
    // typedef std::shared_ptr<CMenu> MenuPtr;
    // typedef std::shared_ptr<MenuItemData> ItemDataPtr;
    // typedef std::shared_ptr<CPalette> PalettePtr;
    // typedef std::shared_ptr<CPen> PenPtr;
    // typedef std::shared_ptr<CPropertyPage> PropertyPagePtr;
    // typedef std::shared_ptr<CRgn> RgnPtr;
    // typedef std::shared_ptr<TLSData> TLSDataPtr;
    // typedef std::shared_ptr<CWinThread> ThreadPtr;
    // typedef std::shared_ptr<CWnd> WndPtr;
    typedef Shared_Ptr<CBitmap> BitmapPtr;
    typedef Shared_Ptr<CBrush> BrushPtr;
    typedef Shared_Ptr<CDC> DCPtr;
    typedef Shared_Ptr<CDocker> DockPtr;
    typedef Shared_Ptr<CFont> FontPtr;
    typedef Shared_Ptr<CGDIObject> GDIPtr;
    typedef Shared_Ptr<CImageList> ImageListPtr;
    typedef Shared_Ptr<CMDIChild> MDIChildPtr;
    typedef Shared_Ptr<CMenu> MenuPtr;
    typedef Shared_Ptr<MenuItemData> ItemDataPtr;
    typedef Shared_Ptr<CPalette> PalettePtr;
    typedef Shared_Ptr<CPen> PenPtr;
    typedef Shared_Ptr<CPropertyPage> PropertyPagePtr;
    typedef Shared_Ptr<CRgn> RgnPtr;
    typedef Shared_Ptr<TLSData> TLSDataPtr;
    typedef Shared_Ptr<CWinThread> ThreadPtr;
    typedef Shared_Ptr<CWnd> WndPtr;


    // A structure that contains the data members for CGDIObject.
    struct CGDI_Data
    {
        // Constructor
        CGDI_Data() : hGDIObject(0), count(1L), isManagedObject(false) {}

        HGDIOBJ hGDIObject;
        long    count;
        bool    isManagedObject;
    };


    // A structure that contains the data members for CImageList.
    struct CIml_Data
    {
        // Constructor
        CIml_Data() : images(0), isManagedHiml(false), count(1L) {}

        HIMAGELIST  images;
        bool        isManagedHiml;
        long        count;
    };

  #ifndef _WIN32_WCE

    // A structure that contains the data members for CMenu.
    struct CMenu_Data
    {
        // Constructor
        CMenu_Data() : menu(0), isManagedMenu(false), count(1L) {}

        std::vector<MenuPtr> vSubMenus; // A vector of smart pointers to CMenu
        HMENU menu;
        bool isManagedMenu;
        long count;
    };

  #endif

    // The comparison function object used by CWinApp::m_mapHDC
    struct CompareHDC
    {
        bool operator()(const HDC a, const HDC b) const
            {return (reinterpret_cast<DWORD_PTR>(a) < reinterpret_cast<DWORD_PTR>(b));}
    };


    // The comparison function object used by CWinApp::m_mapGDI
    struct CompareGDI
    {
        bool operator()(const HGDIOBJ a, const HGDIOBJ b) const
            {return (reinterpret_cast<DWORD_PTR>(a) < reinterpret_cast<DWORD_PTR>(b));}
    };


    // The comparison function object used by CWinApp::m_mapHIMAGELIST
    struct CompareHIMAGELIST
    {
        bool operator()(const HIMAGELIST a, const HIMAGELIST b) const
            {return (reinterpret_cast<DWORD_PTR>(a) < reinterpret_cast<DWORD_PTR>(b));}
    };


    // The comparison function object used by CWinApp::m_mapHMENU
    struct CompareHMENU
    {
        bool operator()(const HMENU a, const HMENU b) const
            {return (reinterpret_cast<DWORD_PTR>(a) < reinterpret_cast<DWORD_PTR>(b));}
    };


    // The comparison function object used by CWinApp::m_mapHWND
    struct CompareHWND
    {
        bool operator()(const HWND a, const HWND b) const
            {return (reinterpret_cast<DWORD_PTR>(a) < reinterpret_cast<DWORD_PTR>(b));}
    };


    // Used for Thread Local Storage (TLS)
    struct TLSData
    {
        CWnd* pWnd;         // pointer to CWnd object for Window creation
        HWND  mainWnd;      //  handle to the main window for the thread (usually CFrame)
        CMenuBar* pMenuBar; // pointer to CMenuBar object used for the WH_MSGFILTER hook
        HHOOK msgHook;      // WH_MSGFILTER hook for CMenuBar and Modal Dialogs
        long  dlgHooks;     // Number of Dialog MSG hooks

        TLSData() : pWnd(0), mainWnd(0), pMenuBar(0), msgHook(0), dlgHooks(0) {} // Constructor
    };


    /////////////////////////////////////////
    // This class is used for thread synchronisation. A critical section object
    // provides synchronization similar to that provided by a mutex object,
    // except that a critical section can be used only by the threads of a
    // single process. Critical sections are faster and more efficient than mutexes.
    // The CCriticalSection object should be created in the primary thread. Create
    // them as member variables in your CWinApp derived class.
    class CCriticalSection
    {
    public:
        CCriticalSection();
        ~CCriticalSection();

        void Lock();
        void Release();

    private:
        CCriticalSection ( const CCriticalSection& );
        CCriticalSection& operator = ( const CCriticalSection& );

        CRITICAL_SECTION m_cs;
        long m_count;
    };


    /////////////////////////////////////////////////////////////////
    // CThreadLock provides a convenient RAII-style mechanism for
    // owning a CCriticalSection for the duration of a scoped block.
    // Automatically locks the specified CCriticalSection when
    // constructed, and releases the critical section when destroyed.
    class CThreadLock
    {
    public:
        CThreadLock(CCriticalSection& cs) : m_cs(cs) { m_cs.Lock(); }
        ~CThreadLock() { m_cs.Release(); }

    private:
        CThreadLock(const CThreadLock&);                // Disable copy construction
        CThreadLock& operator= (const CThreadLock&);    // Disable assignment operator
        CCriticalSection& m_cs;
    };


    ////////////////////////////////////////////////////////////////
    // CHGlobal is a class used to wrap a global memory handle.
    // It automatically frees the global memory when the object goes
    // out of scope. This class is used by CDevMode and CDevNames
    // defined in wxx_printdialogs.h
    class CHGlobal
    {
    public:
        CHGlobal() : m_global(0) {}
        CHGlobal(HGLOBAL handle) : m_global(handle) {}
        CHGlobal(size_t size) : m_global(0) { Alloc(size); }
        ~CHGlobal()                     { Free(); }

        void Alloc(size_t size);
        void Free();
        HGLOBAL Get() const             { return m_global; }
        void Reassign(HGLOBAL global);

        operator HGLOBAL() const        { return m_global; }

    private:
        CHGlobal(const CHGlobal&);              // Disable copy
        CHGlobal& operator = (const CHGlobal&); // Disable assignment

        HGLOBAL m_global;
    };


    ////////////////////////////////////////////////////////////////////
    // The CObject class provides support for Serialization by CArchive.
    class CObject
    {
    public:
        CObject() {}
        virtual ~CObject() {}

        virtual void Serialize(CArchive& ar);
    };


    // typedef for _beginthreadex's callback function.
    typedef UINT (WINAPI *PFNTHREADPROC)(LPVOID);


    //////////////////////////////////////////////////////////////
    // CWinThread manages a thread. It supports GUI threads and
    // worker threads. For a GUI thread, it runs the message loop.
    class CWinThread : public CObject
    {
    public:
        CWinThread();
        CWinThread(PFNTHREADPROC pfnThreadProc, LPVOID pParam);
        virtual ~CWinThread();

        // Overridables
        virtual BOOL InitInstance();
        virtual int MessageLoop();
        virtual BOOL OnIdle(LONG count);
        virtual BOOL PreTranslateMessage(MSG& msg);

        // Operations
        HANDLE  CreateThread(unsigned initflag = 0, unsigned stack_size = 0, LPSECURITY_ATTRIBUTES pSecurityAttributes = NULL);
        HACCEL  GetAcceleratorTable() const { return m_accel; }
        HWND    GetAcceleratorsWindow() const { return m_accelWnd; }
        HWND    GetMainWnd() const;
        HANDLE  GetThread() const;
        int     GetThreadID() const;
        int     GetThreadPriority() const;
        BOOL    IsRunning() const { return (WaitForSingleObject(m_thread, 0) == WAIT_TIMEOUT); }
        BOOL    PostThreadMessage(UINT message, WPARAM wparam, LPARAM lparam) const;
        DWORD   ResumeThread() const;
        void    SetAccelerators(HACCEL accel, HWND hWndAccel);
        void    SetMainWnd(HWND wnd);
        BOOL    SetThreadPriority(int priority) const;
        DWORD   SuspendThread() const;
        operator HANDLE () const { return GetThread(); }

    private:
        CWinThread(const CWinThread&);              // Disable copy construction
        CWinThread& operator = (const CWinThread&); // Disable assignment operator

        static  UINT WINAPI StaticThreadProc(LPVOID pCThread);

        PFNTHREADPROC m_pfnThreadProc;  // Callback function for worker threads
        LPVOID m_pThreadParams;         // Thread parameter for worker threads
        HANDLE m_thread;                // Handle of this thread
        UINT m_threadID;                // ID of this thread
        DWORD m_threadIDForWinCE;       // ID of this thread (for WinCE only)
        HACCEL m_accel;                 // handle to the accelerator table
        HWND m_accelWnd;                // handle to the window for accelerator keys
    };

    ///////////////////////////////////////////////////////////////
    // CWinApp manages the application. Its constructor initializes
    // the Win32++ framework. The Run function calls InitInstance,
    // and starts the message loop on the main thread.
    // There can only be one instance of CWinApp.
    class CWinApp : public CWinThread
    {
        // Provide these access to CWinApp's private members:
        friend class CDC;
        friend class CDialog;
        friend class CGDIObject;
        friend class CImageList;
        friend class CMenu;
        friend class CPageSetupDialog;
        friend class CPrintDialog;
        friend class CPrintDialogEx;
        friend class CPropertyPage;
        friend class CWnd;
        friend CWinApp* GetApp();

    public:
        CWinApp();
        virtual ~CWinApp();

        // Overridables
        virtual BOOL InitInstance();
        virtual int Run();

        // Operations
        CWnd* GetCWndFromMap(HWND wnd);
        HINSTANCE GetInstanceHandle() const { return m_instance; }
        HINSTANCE GetResourceHandle() const { return (m_resource ? m_resource : m_instance); }
        TLSData* GetTlsData() const;
        HCURSOR LoadCursor(LPCTSTR pResourceName) const;
        HCURSOR LoadCursor(int cursorID) const;
        HCURSOR LoadStandardCursor(LPCTSTR pCursorName) const;
        HICON   LoadIcon(LPCTSTR pResourceName) const;
        HICON   LoadIcon(int iconID) const;
        HICON   LoadStandardIcon(LPCTSTR pIconName) const;
        HANDLE  LoadImage(LPCTSTR pResourceName, UINT type, int cx, int  cy, UINT flags = LR_DEFAULTCOLOR) const;
        HANDLE  LoadImage(int imageID, UINT type, int cx, int cy, UINT flags = LR_DEFAULTCOLOR) const;
        HCURSOR SetCursor(HCURSOR cursor) const;
        void    SetResourceHandle(HINSTANCE resource);
        TLSData* SetTlsData();

    private:
        CWinApp(const CWinApp&);                // Disable copy construction
        CWinApp& operator = (const CWinApp&);   // Disable assignment operator

        void AddCDCData(HDC dc, CDC_Data* pData);
        void AddCGDIData(HGDIOBJ gdi, CGDI_Data* pData);
        void AddCImlData(HIMAGELIST images, CIml_Data* pData);
        CDC_Data* GetCDCData(HDC dc);
        CGDI_Data* GetCGDIData(HGDIOBJ object);
        CIml_Data* GetCImlData(HIMAGELIST images);
        void SetCallback();
        static CWinApp* SetnGetThis(CWinApp* pThis = 0, bool reset = false);
        void UpdateDefaultPrinter();

        std::map<HDC, CDC_Data*, CompareHDC> m_mapCDCData;
        std::map<HGDIOBJ, CGDI_Data*, CompareGDI> m_mapCGDIData;
        std::map<HIMAGELIST, CIml_Data*, CompareHIMAGELIST> m_mapCImlData;
        std::map<HWND, CWnd*, CompareHWND> m_mapHWND;       // maps window handles to CWnd objects
        std::vector<TLSDataPtr> m_allTLSData;     // vector of TLSData smart pointers, one for each thread
        CCriticalSection m_appLock;   // thread synchronization for CWinApp and TLS.
        CCriticalSection m_gdiLock;   // thread synchronization for m_mapCDCData and m_mapCGDIData.
        CCriticalSection m_wndLock;   // thread synchronization for m_mapHWND etc.
        CCriticalSection m_printLock; // thread synchronization for printing.
        HINSTANCE m_instance;         // handle to the application's instance
        HINSTANCE m_resource;         // handle to the application's resources
        DWORD m_tlsData;              // Thread Local Storage data
        WNDPROC m_callback;           // callback address of CWnd::StaticWndowProc
        CHGlobal m_devMode;           // Used by CPrintDialog and CPageSetupDialog
        CHGlobal m_devNames;          // Used by CPrintDialog and CPageSetupDialog

#ifndef _WIN32_WCE
        void AddCMenuData(HMENU menu, CMenu_Data* pData);
        CMenu_Data* GetCMenuData(HMENU menu);
        std::map<HMENU, CMenu_Data*, CompareHMENU> m_mapCMenuData;
#endif

    public:
        // Messages used for exceptions.
        virtual CString MsgAppThread() const;
        virtual CString MsgArReadFail() const;
        virtual CString MsgArNotCStringA() const;
        virtual CString MsgArNotCStringW() const;
        virtual CString MsgCriticalSection() const;
        virtual CString MsgMtxEvent() const;
        virtual CString MsgMtxMutex() const;
        virtual CString MsgMtxSemaphore() const;

        virtual CString MsgWndCreate() const;
        virtual CString MsgWndDialog() const;
        virtual CString MsgWndGlobalLock() const;
        virtual CString MsgWndPropertSheet() const;
        virtual CString MsgSocWSAStartup() const;
        virtual CString MsgSocWS2Dll() const;
        virtual CString MsgIPControl() const;
        virtual CString MsgRichEditDll() const;
        virtual CString MsgTaskDialog() const;

        virtual CString MsgFileClose() const;
        virtual CString MsgFileFlush() const;
        virtual CString MsgFileLock() const;
        virtual CString MsgFileOpen() const;
        virtual CString MsgFileRead() const;
        virtual CString MsgFileRename() const;
        virtual CString MsgFileRemove() const;
        virtual CString MsgFileLength() const;
        virtual CString MsgFileUnlock() const;
        virtual CString MsgFileWrite() const;

        virtual CString MsgGdiDC() const;
        virtual CString MsgGdiIC() const;
        virtual CString MsgGdiBitmap() const;
        virtual CString MsgGdiBrush() const;
        virtual CString MsgGdiFont() const;
        virtual CString MsgGdiPalette() const;
        virtual CString MsgGdiPen() const;
        virtual CString MsgGdiRegion() const;
        virtual CString MsgGdiGetDC() const;
        virtual CString MsgGdiGetDCEx() const;
        virtual CString MsgGdiSelObject() const;
        virtual CString MsgGdiGetWinDC() const;
        virtual CString MsgGdiBeginPaint() const;

        virtual CString MsgImageList() const;
        virtual CString MsgMenu() const;
        virtual CString MsgPrintFound() const;

        // DDX anomaly prompting messages
        virtual CString MsgDDX_Byte() const;
        virtual CString MsgDDX_Int() const;
        virtual CString MsgDDX_Long() const;
        virtual CString MsgDDX_Short() const;
        virtual CString MsgDDX_Real() const;
        virtual CString MsgDDX_UINT() const;
        virtual CString MsgDDX_ULONG() const;

        // DDV formats and prompts
        virtual CString MsgDDV_IntRange() const;
        virtual CString MsgDDV_UINTRange() const;
        virtual CString MsgDDV_RealRange() const;
        virtual CString MsgDDV_StringSize() const;
    };


    // Global function declarations
    inline CWinApp* GetApp();
    inline void StrCopyA(char* dst, const char* src, size_t dst_size);
    inline void StrCopyW(wchar_t* dst, const wchar_t* src, size_t dst_size);
    inline void StrCopy(TCHAR* dst, const TCHAR* src, size_t dst_size);


} // namespace Win32xx


#endif // _WIN32XX_APPCORE0_H_
