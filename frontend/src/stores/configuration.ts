import { defineStore } from 'pinia'

import {
  createAttributeDefinitionApi,
  createCategoryApi,
  createFamilyMemberApi,
  createLocationNodeApi,
  createResidenceApi,
  fetchConfigBootstrapApi,
  type AttributeDefinitionCreate,
  type CategoryCreate,
  type ConfigBootstrap,
  type FamilyMemberCreate,
  type LocationNodeCreate,
  type ResidenceCreate
} from '../api/configuration'

interface ConfigurationState {
  data: ConfigBootstrap | null
  loading: boolean
}

export const useConfigurationStore = defineStore('configuration', {
  state: (): ConfigurationState => ({ data: null, loading: false }),
  actions: {
    async load() {
      this.loading = true
      try {
        this.data = await fetchConfigBootstrapApi()
      } finally {
        this.loading = false
      }
    },
    async createResidence(payload: ResidenceCreate) {
      await createResidenceApi(payload)
      await this.load()
    },
    async createLocationNode(payload: LocationNodeCreate) {
      await createLocationNodeApi(payload)
      await this.load()
    },
    async createFamilyMember(payload: FamilyMemberCreate) {
      await createFamilyMemberApi(payload)
      await this.load()
    },
    async createCategory(payload: CategoryCreate) {
      await createCategoryApi(payload)
      await this.load()
    },
    async createAttributeDefinition(payload: AttributeDefinitionCreate) {
      await createAttributeDefinitionApi(payload)
      await this.load()
    }
  }
})
