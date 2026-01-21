/**
 * Tests for RBACService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { rbacService } from '@/services/rbac-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

describe('RBACService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Role Operations', () => {
    it('getAllRoles returns list of roles', async () => {
      const result = await rbacService.getAllRoles()
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })

    it('getRoleById returns single role', async () => {
      const result = await rbacService.getRoleById('role-1')
      
      expect(result).toMatchObject({
        id: 'role-1',
        name: expect.any(String),
      })
    })

    it('createRole creates new role', async () => {
      const roleData = {
        name: 'new_role',
        description: 'A new role',
      }

      const result = await rbacService.createRole(roleData)
      
      expect(result).toMatchObject({
        name: 'new_role',
      })
    })

    it('updateRole updates role', async () => {
      const updateData = { description: 'Updated description' }
      
      const result = await rbacService.updateRole('role-1', updateData)
      
      expect(result).toMatchObject({
        id: 'role-1',
      })
    })

    it('deleteRole deletes role', async () => {
      await expect(rbacService.deleteRole('role-1')).resolves.not.toThrow()
    })
  })

  describe('Permission Operations', () => {
    it('getAllPermissions returns list of permissions', async () => {
      const result = await rbacService.getAllPermissions()
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })

    it('getPermissionById returns single permission', async () => {
      const result = await rbacService.getPermissionById('perm-1')
      
      expect(result).toMatchObject({
        id: 'perm-1',
        name: expect.any(String),
      })
    })

    it('createPermission creates new permission', async () => {
      const permData = {
        name: 'agents:write',
        description: 'Write agents',
        resource: 'agents',
        action: 'write',
      }

      const result = await rbacService.createPermission(permData)
      
      expect(result).toMatchObject({
        name: 'agents:write',
      })
    })

    it('updatePermission updates permission', async () => {
      const updateData = { description: 'Updated description' }
      
      const result = await rbacService.updatePermission('perm-1', updateData)
      
      expect(result).toMatchObject({
        id: 'perm-1',
      })
    })

    it('deletePermission deletes permission', async () => {
      await expect(rbacService.deletePermission('perm-1')).resolves.not.toThrow()
    })
  })

  describe('Role-Permission Operations', () => {
    it('getPermissionsForRole returns permissions', async () => {
      const result = await rbacService.getPermissionsForRole('role-1')
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })

    it('assignPermissionToRole assigns permission', async () => {
      const result = await rbacService.assignPermissionToRole('role-1', 'perm-1')
      
      expect(result).toMatchObject({
        role_id: 'role-1',
        permission_id: 'perm-1',
      })
    })

    it('removePermissionFromRole removes permission', async () => {
      await expect(rbacService.removePermissionFromRole('role-1', 'perm-1')).resolves.not.toThrow()
    })
  })

  describe('User-Role Operations', () => {
    it('getRolesForUser returns roles', async () => {
      const result = await rbacService.getRolesForUser('user-1')
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })

    it('getRolesForUser with organization ID', async () => {
      const result = await rbacService.getRolesForUser('user-1', 'org-1')
      
      expect(result).toHaveLength(1)
    })

    it('getUserRolesWithPermissions returns roles with permissions', async () => {
      const result = await rbacService.getUserRolesWithPermissions('user-1')
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        permissions: expect.any(Array),
      })
    })

    it('assignRoleToUser assigns role', async () => {
      const userRoleData = {
        user_id: 'user-1',
        role_id: 'role-1',
        organization_id: 'org-1',
      }

      const result = await rbacService.assignRoleToUser(userRoleData)
      
      expect(result).toMatchObject({
        user_id: 'user-1',
        role_id: 'role-1',
      })
    })

    it('updateUserRole updates user role', async () => {
      const updateData = { role_id: 'role-2' }
      
      const result = await rbacService.updateUserRole('user-role-1', updateData)
      
      expect(result).toMatchObject({
        id: 'user-role-1',
      })
    })

    it('removeRoleFromUser removes role', async () => {
      await expect(rbacService.removeRoleFromUser('user-role-1')).resolves.not.toThrow()
    })
  })

  describe('Permission/Role Checks', () => {
    it('userHasPermission returns boolean', async () => {
      const result = await rbacService.userHasPermission('user-1', 'agents:read')
      
      expect(result).toBe(true)
    })

    it('userHasPermission with organization ID', async () => {
      const result = await rbacService.userHasPermission('user-1', 'agents:read', 'org-1')
      
      expect(result).toBe(true)
    })

    it('userHasRole returns boolean', async () => {
      const result = await rbacService.userHasRole('user-1', 'org_admin')
      
      expect(result).toBe(true)
    })

    it('userHasRole with organization ID', async () => {
      const result = await rbacService.userHasRole('user-1', 'org_admin', 'org-1')
      
      expect(result).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('handles 404 errors', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/rbac/roles/:roleId`, () => {
          return new HttpResponse(null, { status: 404 })
        })
      )

      await expect(rbacService.getRoleById('invalid-id')).rejects.toThrow()
    })

    it('handles 403 forbidden', async () => {
      server.use(
        http.post(`${API_BASE_URL}/api/v1/rbac/roles`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Forbidden' }), { status: 403 })
        })
      )

      await expect(rbacService.createRole({ name: 'test', description: 'test' })).rejects.toThrow()
    })

    it('handles 500 errors', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/rbac/roles`, () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(rbacService.getAllRoles()).rejects.toThrow()
    })
  })
})
