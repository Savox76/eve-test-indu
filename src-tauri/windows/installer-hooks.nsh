; Keep program-folder data during upgrades and normal uninstall unless the user
; explicitly selects Tauri's "Delete application data" checkbox.
!macro NSIS_HOOK_PREUNINSTALL
  ${If} $DeleteAppDataCheckboxState = 1
  ${AndIf} $UpdateMode <> 1
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\data-before-appdata-migration"
    StrCpy $0 1
    delete_previous_program_data_loop:
      RMDir /r "$INSTDIR\data-before-appdata-migration-$0"
      IntOp $0 $0 + 1
      IntCmp $0 100 delete_previous_program_data_done delete_previous_program_data_loop delete_previous_program_data_done
    delete_previous_program_data_done:
  ${EndIf}
!macroend
